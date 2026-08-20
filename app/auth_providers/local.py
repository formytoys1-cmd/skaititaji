"""Локальный провайдер аутентификации: email + пароль (AUTH-001).

Оформляет существующий вход (app/auth.authenticate) как один из провайдеров,
сохраняя полную обратную совместимость: логика проверки пароля не меняется.
"""
from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.auth import authenticate
from app.auth_providers.base import (
    AuthError,
    AuthProvider,
    AuthResult,
    VerifiedIdentity,
)

PROVIDER_CODE = "local"


class LocalAuthProvider(AuthProvider):
    """Классический вход по email и паролю."""

    provider_code = PROVIDER_CODE

    def __init__(self, session: Session) -> None:
        self._session = session

    def start(self, **params: Any) -> AuthResult:
        # Локальный вход не требует внешней сессии — форма отдаётся сразу.
        return AuthResult(provider=self.provider_code, session_id="local")

    def callback(self, *, email: str = "", password: str = "", **_: Any) -> VerifiedIdentity:
        user = authenticate(self._session, email, password)
        if not user:
            raise AuthError("rejected", "Nepareizs e-pasts vai parole.")
        return VerifiedIdentity(
            provider=self.provider_code,
            subject=str(user.id),
            full_name=user.full_name,
            email=user.email,
        )
