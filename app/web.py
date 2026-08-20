"""Утилиты веб-слоя: Jinja2-шаблоны, единый рендер, flash и i18n."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.i18n import LANG_NAMES, LANGS, meter_name, normalize_lang, t
from app.models import Organization, User

templates = Jinja2Templates(directory="app/templates")


def _announcement(org: Optional[Organization], lang: str) -> Optional[str]:
    """Баннер-объявление: если у организации открыто окно подачи — показываем
    дедлайн. Уместно для utility (снижает нагрузку на поддержку)."""
    if not org:
        return None
    try:

        from app.services import is_window_open
        if is_window_open(org):
            return t(lang, "announce.window_open").format(day=org.reading_day_to)
    except Exception:
        return None
    return None


def flash(request: Request, text: str, level: str = "info") -> None:
    msgs = request.session.get("_messages", [])
    msgs.append({"text": text, "level": level})
    request.session["_messages"] = msgs


def _pop_messages(request: Request) -> list[dict]:
    msgs = request.session.get("_messages", [])
    if msgs:
        request.session["_messages"] = []
    return msgs


def current_lang(request: Request) -> str:
    return normalize_lang(request.cookies.get("lang"))


def render(
    request: Request,
    template: str,
    context: Optional[dict[str, Any]] = None,
    *,
    current_user: Optional[User] = None,
    org: Optional[Organization] = None,
    status_code: int = 200,
) -> HTMLResponse:
    lang = current_lang(request)
    ctx: dict[str, Any] = {
        "request": request,
        "app_name": settings.app_name,
        "app_tagline": settings.app_tagline,
        "current_user": current_user,
        "org": org,
        "brand_color": (org.brand_color if org else "#0369a1"),
        "flash_messages": _pop_messages(request),
        # i18n
        "lang": lang,
        "langs": LANGS,
        "lang_names": LANG_NAMES,
        "t": lambda key: t(lang, key),
        "meter_name": lambda mt: meter_name(mt, lang),
        "announcement": _announcement(org, lang),
        "today": __import__("datetime").date.today(),
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(
        request, template, ctx, status_code=status_code
    )
