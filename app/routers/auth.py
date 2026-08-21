"""Вход и выход."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.antibot import (
    HONEYPOT_FIELD,
    TIMESTAMP_FIELD,
    check_human,
    make_timestamp_token,
)
from app.auth import (
    authenticate,
    get_current_user,
    hash_password,
    login_user,
    logout_user,
)
from app.auth_providers.base import AuthError, resolve_user
from app.auth_providers.registry import get_auth_provider
from app.config import settings
from app.csrf import csrf_protect
from app.database import get_session
from app.email import send_email, verification_email
from app.i18n import normalize_lang
from app.models import (
    Building,
    Unit,
    UnitResident,
    User,
    UserRole,
)
from app.ratelimit import auth_limiter, client_ip
from app.verification import create_verification, verify_token
from app.web import flash, render

router = APIRouter()

_ROLE_HOME = {
    UserRole.RESIDENT: "/dzivoklis",
    UserRole.MANAGER: "/parvalde",
    UserRole.SUPERADMIN: "/admin",
}

# Единый ответ для неуспешной аутентификации (SEC-006, анти-enumeration):
# один и тот же текст независимо от того, существует ли email.
_AUTH_FAILED_MSG = "Nepareizs e-pasts vai parole."


def _rate_limit(request: Request, scope: str, identity: str) -> float | None:
    """Проверяет лимит попыток по IP+identity. Возвращает retry_after (сек),
    если запрос нужно отклонить (429), иначе None. Дополнительно применяет
    экспоненциальную задержку между попытками (анти-брутфорс)."""
    import time

    key = f"{scope}:{client_ip(request)}:{identity.lower().strip()}"
    delay = auth_limiter.delay_for(key)
    if delay > 0:
        time.sleep(min(delay, 2.0))  # ограничиваем, чтобы не держать воркер долго
    allowed, retry_after = auth_limiter.hit(key)
    return None if allowed else retry_after


@router.get("/login")
def login_form(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    if current_user:
        return RedirectResponse(_ROLE_HOME.get(current_user.role, "/"), 303)
    return render(request, "login.html", current_user=None)


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    retry_after = _rate_limit(request, "login", email)
    if retry_after is not None:
        flash(request, "Pārāk daudz mēģinājumu. Mēģiniet vēlāk.", "error")
        resp = render(request, "login.html", current_user=None, status_code=429)
        resp.headers["Retry-After"] = str(int(retry_after) + 1)
        return resp
    user = authenticate(session, email, password)
    if not user:
        # SEC-006: единый ответ без раскрытия существования email.
        flash(request, _AUTH_FAILED_MSG, "error")
        return RedirectResponse("/login", 303)
    # Гейт подтверждения e-mail: непроверенный локальный аккаунт не входит.
    # (eIDAS/демо-аккаунты помечены verified, поэтому их это не касается.)
    if settings.require_email_verification and not user.is_verified:
        flash(request,
              "E-pasts nav apstiprināts. Pārbaudiet pastu vai pieprasiet jaunu "
              "saiti.", "error")
        return RedirectResponse("/verificet/atkartot", 303)
    login_user(request, user)
    flash(request, f"Sveiki, {user.full_name}!", "success")
    return RedirectResponse(_ROLE_HOME.get(user.role, "/"), 303)


@router.get("/demo-login")
def demo_login(
    request: Request,
    role: str = "resident",
    session: Session = Depends(get_session),
):
    """Гостевой вход в один клик под демо-аккаунтом выбранной роли."""
    # SEC-001: обход аутентификации недопустим в проде. Эндпоинт существует
    # только в dev/демо; при выключенном demo-login отвечаем 404 (как будто
    # маршрута нет), чтобы не раскрывать его наличие.
    if not settings.demo_login_enabled:
        raise HTTPException(status_code=404)
    retry_after = _rate_limit(request, "demo-login", role)
    if retry_after is not None:
        flash(request, "Pārāk daudz mēģinājumu. Mēģiniet vēlāk.", "error")
        resp = RedirectResponse("/login", 303)
        resp.status_code = 429
        resp.headers["Retry-After"] = str(int(retry_after) + 1)
        return resp
    emails = {
        "resident": "resident@demo.lv",
        "manager": "manager@demo.lv",
        "admin": "admin@demo.lv",
    }
    email = emails.get(role, "resident@demo.lv")
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        flash(request, "Demo konts nav atrasts.", "error")
        return RedirectResponse("/login", 303)
    login_user(request, user)
    return RedirectResponse(_ROLE_HOME.get(user.role, "/"), 303)


@router.get("/lang/{code}")
def set_language(request: Request, code: str):
    """Переключение языка интерфейса (сохраняется в cookie)."""
    lang = normalize_lang(code)
    referer = request.headers.get("referer", "/")
    resp = RedirectResponse(referer, 303)
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp.set_cookie(
        "lang", lang, max_age=60 * 60 * 24 * 365,
        samesite="lax", httponly=True, secure=secure,
    )
    return resp


# --------------------------------------------------------------------------- #
# eIDAS-вход: банк / Smart-ID / eParaksts (AUTH-001)
# --------------------------------------------------------------------------- #
@router.get("/eidas/login")
def eidas_login_form(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    if current_user:
        return RedirectResponse(_ROLE_HOME.get(current_user.role, "/"), 303)
    return render(request, "eidas_login.html", current_user=None)


@router.post("/eidas/login")
def eidas_login_submit(
    request: Request,
    identifier: str = Form(...),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    """Единый поток eIDAS (start→callback) для демо/mock-режима.

    В mock-режиме (дефолт) внешний вызов эмулируется, поэтому старт и callback
    выполняются сразу. С реальным провайдером здесь будет промежуточный экран
    ожидания подтверждения на устройстве пользователя.
    """
    identifier = identifier.strip()
    retry_after = _rate_limit(request, "eidas", identifier)
    if retry_after is not None:
        flash(request, "Pārāk daudz mēģinājumu. Mēģiniet vēlāk.", "error")
        resp = render(request, "eidas_login.html", current_user=None, status_code=429)
        resp.headers["Retry-After"] = str(int(retry_after) + 1)
        return resp

    provider = get_auth_provider("eidas")
    try:
        started = provider.start(identifier=identifier)
        identity = provider.callback(
            session_id=started.session_id, identifier=identifier
        )
    except AuthError:
        # Единый ответ без раскрытия деталей (SEC-006).
        flash(request, "eIDAS autentifikācija neizdevās.", "error")
        return RedirectResponse("/eidas/login", 303)

    user = resolve_user(session, identity)
    if user is None:
        # Личность подтверждена, но аккаунта нет — направляем на регистрацию.
        session.commit()
        flash(
            request,
            "Autentifikācija veiksmīga. Lūdzu, reģistrējieties ar konta numuru.",
            "info",
        )
        return RedirectResponse("/registreties", 303)

    if not user.is_active:
        flash(request, "Konts ir deaktivizēts.", "error")
        return RedirectResponse("/eidas/login", 303)

    session.commit()  # фиксируем привязку external_subject, сделанную resolve_user
    login_user(request, user)
    flash(request, f"Sveiki, {user.full_name}!", "success")
    return RedirectResponse(_ROLE_HOME.get(user.role, "/"), 303)


# --------------------------------------------------------------------------- #
# Самрегистрация жителя (привязка к квартире по лицевому счёту)
# --------------------------------------------------------------------------- #
def _send_verification(request: Request, user: User, session: Session) -> str:
    """Создаёт токен, отправляет письмо и возвращает ссылку подтверждения."""
    ev = create_verification(session, user)
    link = f"{settings.public_base_url}/verificet?token={ev.token}"
    subject, body = verification_email(user.full_name, link, settings.app_name)
    send_email(user.email, subject, body)
    return link


def _antibot_ctx() -> dict:
    """Контекст для форм с анти-бот полями."""
    return {
        "form_ts": make_timestamp_token(),
        "honeypot_field": HONEYPOT_FIELD,
        "ts_field": TIMESTAMP_FIELD,
    }


@router.get("/registreties")
def register_form(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    if current_user:
        return RedirectResponse(_ROLE_HOME.get(current_user.role, "/"), 303)
    return render(request, "register.html", _antibot_ctx(), current_user=None)


@router.post("/registreties")
def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    account_number: str = Form(...),
    company: str = Form(default=""),        # honeypot (HONEYPOT_FIELD)
    form_ts: str = Form(default=""),        # подписанная метка времени (TIMESTAMP_FIELD)
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    email = email.lower().strip()
    account_number = account_number.strip()

    # Анти-бот: honeypot + подписанная метка времени формы (free, без сервисов).
    # Единый мягкий ответ, чтобы не подсказывать боту, что именно не так.
    if not check_human(company, form_ts):
        flash(request, "Neizdevās apstrādāt formu. Mēģiniet vēlreiz.", "error")
        return RedirectResponse("/registreties", 303)

    retry_after = _rate_limit(request, "register", email)
    if retry_after is not None:
        flash(request, "Pārāk daudz mēģinājumu. Mēģiniet vēlāk.", "error")
        resp = render(request, "register.html", _antibot_ctx(),
                      current_user=None, status_code=429)
        resp.headers["Retry-After"] = str(int(retry_after) + 1)
        return resp

    if len(password) < 6:
        flash(request, "Parolei jābūt vismaz 6 rakstzīmes.", "error")
        return RedirectResponse("/registreties", 303)

    # Квартира по лицевому счёту (его выдаёт управляющий)
    unit = session.exec(
        select(Unit).where(Unit.account_number == account_number)
    ).first()
    if not unit:
        flash(request, "Konta numurs nav atrasts. Sazinieties ar apsaimniekotāju.",
              "error")
        return RedirectResponse("/registreties", 303)

    # Вместимость квартиры (запас ×2): не больше max_residents жильцов на квартиру.
    if unit.max_residents and unit.max_residents > 0:
        current = session.exec(
            select(func.count(UnitResident.id))
            .where(UnitResident.unit_id == unit.id)
        ).one()
        if current >= unit.max_residents:
            flash(request,
                  "Šim dzīvoklim jau ir reģistrēts maksimālais lietotāju skaits. "
                  "Sazinieties ar apsaimniekotāju.", "error")
            return RedirectResponse("/registreties", 303)

    # Уже есть пользователь с таким email?
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        flash(request, "Lietotājs ar šādu e-pastu jau eksistē. Ieejiet sistēmā.",
              "error")
        return RedirectResponse("/login", 303)

    # Организация — по дому квартиры
    building = session.get(Building, unit.building_id)
    org_id = building.organization_id if building else None

    verified = not settings.require_email_verification
    user = User(
        organization_id=org_id, email=email, full_name=full_name.strip(),
        password_hash=hash_password(password), role=UserRole.RESIDENT,
        is_verified=verified,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    session.add(UnitResident(user_id=user.id, unit_id=unit.id, relation="owner"))
    session.commit()

    if settings.require_email_verification:
        link = _send_verification(request, user, session)
        flash(request,
              "Reģistrācija gandrīz pabeigta! Nosūtījām apstiprinājuma saiti uz "
              f"{email}. Atveriet to, lai aktivizētu kontu.", "success")
        # Free-режим без SMTP: показываем ссылку прямо на экране (это ссылка
        # самого пользователя), чтобы демо работало без почтового сервера.
        dev_link = None if settings.email_configured else link
        return render(request, "verify_sent.html", {"dev_link": dev_link},
                      current_user=None)

    login_user(request, user)
    flash(request, f"Reģistrācija veiksmīga! Sveiki, {user.full_name}.", "success")
    return RedirectResponse("/dzivoklis", 303)


@router.get("/registreties/parbaudiet")
def register_check_email(request: Request):
    """Экран «проверьте почту» после регистрации."""
    return render(request, "verify_sent.html", {"dev_link": None},
                  current_user=None)


@router.get("/verificet")
def verify_email_link(
    request: Request,
    token: str = "",
    session: Session = Depends(get_session),
):
    """Переход по ссылке из письма: подтверждает e-mail и входит."""
    user = verify_token(session, token)
    if not user:
        flash(request,
              "Saite nederīga vai novecojusi. Pieprasiet jaunu apstiprinājumu.",
              "error")
        return RedirectResponse("/verificet/atkartot", 303)
    login_user(request, user)
    flash(request, f"E-pasts apstiprināts! Sveiki, {user.full_name}.", "success")
    return RedirectResponse(_ROLE_HOME.get(user.role, "/"), 303)


@router.get("/verificet/atkartot")
def resend_form(request: Request):
    return render(request, "verify_resend.html", _antibot_ctx(),
                  current_user=None)


@router.post("/verificet/atkartot")
def resend_submit(
    request: Request,
    email: str = Form(...),
    company: str = Form(default=""),
    form_ts: str = Form(default=""),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    email = email.lower().strip()
    if not check_human(company, form_ts):
        flash(request, "Neizdevās apstrādāt formu. Mēģiniet vēlreiz.", "error")
        return RedirectResponse("/verificet/atkartot", 303)
    retry_after = _rate_limit(request, "resend", email)
    if retry_after is not None:
        flash(request, "Pārāk daudz mēģinājumu. Mēģiniet vēlāk.", "error")
        resp = render(request, "verify_resend.html", _antibot_ctx(),
                      current_user=None, status_code=429)
        resp.headers["Retry-After"] = str(int(retry_after) + 1)
        return resp
    # Анти-enumeration: ответ одинаковый вне зависимости от наличия аккаунта.
    user = session.exec(select(User).where(User.email == email)).first()
    if user and not user.is_verified:
        _send_verification(request, user, session)
    flash(request,
          "Ja konts eksistē un nav apstiprināts, nosūtījām jaunu saiti uz e-pastu.",
          "info")
    return RedirectResponse("/login", 303)


@router.get("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/", 303)
