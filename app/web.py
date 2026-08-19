"""Утилиты веб-слоя: Jinja2-шаблоны, единый рендер и flash-сообщения."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.models import Organization, User

templates = Jinja2Templates(directory="app/templates")


def flash(request: Request, text: str, level: str = "info") -> None:
    msgs = request.session.get("_messages", [])
    msgs.append({"text": text, "level": level})
    request.session["_messages"] = msgs


def _pop_messages(request: Request) -> list[dict]:
    msgs = request.session.get("_messages", [])
    if msgs:
        request.session["_messages"] = []
    return msgs


def render(
    request: Request,
    template: str,
    context: Optional[dict[str, Any]] = None,
    *,
    current_user: Optional[User] = None,
    org: Optional[Organization] = None,
    status_code: int = 200,
) -> HTMLResponse:
    ctx: dict[str, Any] = {
        "request": request,
        "app_name": settings.app_name,
        "app_tagline": settings.app_tagline,
        "current_user": current_user,
        "org": org,
        "brand_color": (org.brand_color if org else "#0ea5e9"),
        "messages": _pop_messages(request),
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(
        request, template, ctx, status_code=status_code
    )
