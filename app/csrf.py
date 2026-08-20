"""CSRF-защита (SEC-005).

Модель угрозы: cookie-сессия (SameSite=Lax) сама по себе не защищает от всех
CSRF-сценариев (например, top-level POST-навигации, старые браузеры). Поэтому
каждый мутирующий POST дополнительно требует секретный токен, привязанный к
конкретной сессии пользователя.

Механика (синхронизированный токен, «synchronizer token pattern»):
- при первом обращении токен генерируется и кладётся в подписанную сессию;
- шаблоны выводят его в скрытом поле `csrf_token` во всех формах;
- зависимость `csrf_protect` сверяет присланное поле с токеном сессии в
  постоянном по времени сравнении и отклоняет запрос (403) при несовпадении.
"""
from __future__ import annotations

import hmac
import secrets

from fastapi import Form, HTTPException, Request, status

_SESSION_KEY = "_csrf_token"
_FIELD_NAME = "csrf_token"


def get_csrf_token(request: Request) -> str:
    """Возвращает CSRF-токен сессии, создавая его при необходимости."""
    token = request.session.get(_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[_SESSION_KEY] = token
    return token


def validate_csrf(request: Request, submitted: str | None) -> bool:
    expected = request.session.get(_SESSION_KEY)
    if not expected or not submitted:
        return False
    return hmac.compare_digest(str(expected), str(submitted))


async def csrf_protect(
    request: Request,
    csrf_token: str | None = Form(default=None),
) -> None:
    """FastAPI-зависимость: обязательна на всех мутирующих POST-эндпоинтах."""
    if not validate_csrf(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF verification failed",
        )
