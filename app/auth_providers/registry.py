"""Реестр провайдеров аутентификации (AUTH-001).

Добавление нового способа входа — одна строка в ``_PROVIDERS``.
"""
from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from app.auth_providers.base import AuthProvider
from app.auth_providers.eidas import EidasAuthProvider
from app.auth_providers.local import LocalAuthProvider

_PROVIDERS = {
    LocalAuthProvider.provider_code: LocalAuthProvider,
    EidasAuthProvider.provider_code: EidasAuthProvider,
}


def available_providers() -> list[str]:
    return list(_PROVIDERS)


def get_auth_provider(
    provider_code: str, session: Optional[Session] = None
) -> AuthProvider:
    """Вернуть провайдер по коду.

    Локальному провайдеру нужна сессия БД (проверка пароля); eIDAS — нет
    (личность проверяется у внешнего провайдера, маппинг на User делает
    вызывающий код через ``resolve_user``).
    """
    cls = _PROVIDERS.get(provider_code)
    if cls is None:
        raise ValueError(f"Nezināms autentifikācijas veids: {provider_code}")
    if cls is LocalAuthProvider:
        if session is None:
            raise ValueError("Local provider requires a DB session")
        return LocalAuthProvider(session)
    return cls()
