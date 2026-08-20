"""Подключаемые провайдеры аутентификации (AUTH-001).

Абстракция позволяет добавлять способы входа (локальный email+пароль,
eIDAS: банк / Smart-ID / eParaksts), не меняя код маршрутов — только добавляя
реализацию провайдера и строку в реестр.
"""
from app.auth_providers.base import (  # noqa: F401
    AuthError,
    AuthProvider,
    AuthResult,
    VerifiedIdentity,
    resolve_user,
)
from app.auth_providers.registry import get_auth_provider  # noqa: F401
