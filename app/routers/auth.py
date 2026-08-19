"""Вход и выход."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.auth import (
    authenticate,
    get_current_user,
    hash_password,
    login_user,
    logout_user,
)
from app.database import get_session
from app.i18n import normalize_lang
from app.models import (
    Building,
    Organization,
    Unit,
    UnitResident,
    User,
    UserRole,
)
from app.web import flash, render

router = APIRouter()

_ROLE_HOME = {
    UserRole.RESIDENT: "/dzivoklis",
    UserRole.MANAGER: "/parvalde",
    UserRole.SUPERADMIN: "/admin",
}


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
):
    user = authenticate(session, email, password)
    if not user:
        flash(request, "Nepareizs e-pasts vai parole.", "error")
        return RedirectResponse("/login", 303)
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
# Самрегистрация жителя (привязка к квартире по лицевому счёту)
# --------------------------------------------------------------------------- #
@router.get("/registreties")
def register_form(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    if current_user:
        return RedirectResponse(_ROLE_HOME.get(current_user.role, "/"), 303)
    return render(request, "register.html", current_user=None)


@router.post("/registreties")
def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    account_number: str = Form(...),
    session: Session = Depends(get_session),
):
    email = email.lower().strip()
    account_number = account_number.strip()

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

    # Уже есть пользователь с таким email?
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        flash(request, "Lietotājs ar šādu e-pastu jau eksistē. Ieejiet sistēmā.",
              "error")
        return RedirectResponse("/login", 303)

    # Организация — по дому квартиры
    building = session.get(Building, unit.building_id)
    org_id = building.organization_id if building else None

    user = User(
        organization_id=org_id, email=email, full_name=full_name.strip(),
        password_hash=hash_password(password), role=UserRole.RESIDENT,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    session.add(UnitResident(user_id=user.id, unit_id=unit.id, relation="owner"))
    session.commit()

    login_user(request, user)
    flash(request, f"Reģistrācija veiksmīga! Sveiki, {user.full_name}.", "success")
    return RedirectResponse("/dzivoklis", 303)


@router.get("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/", 303)
