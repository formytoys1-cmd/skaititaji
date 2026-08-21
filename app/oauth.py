"""Конфигурация OAuth 2.0 / OpenID Connect провайдеров входа.

«Вход через проверенный сервис» (Google, Microsoft, GitHub) — стандартный и
бесплатный способ аутентификации. Каждый провайдер описывается пресетом
(endpoints + scope), а секреты (client_id/secret) читаются ТОЛЬКО из окружения:

    <PROVIDER>_CLIENT_ID / <PROVIDER>_CLIENT_SECRET
    напр. GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

Провайдер считается включённым, только если заданы оба секрета. Ничего не
хранится в репозитории; если провайдер не настроен — его кнопка не показывается,
а попытка входа даёт понятную ошибку.

Добавить нового провайдера = одна запись в PRESETS.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OAuthProviderConfig:
    code: str
    display_name: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    # Ключи полей в ответе userinfo (у провайдеров различаются).
    subject_field: str = "sub"
    email_field: str = "email"
    name_field: str = "name"
    # Доп. параметры к authorize (например, prompt/access_type у Google).
    extra_authorize_params: dict[str, str] = field(default_factory=dict)
    # Некоторым провайдерам (GitHub) e-mail нужно тянуть отдельным запросом.
    emails_url: str = ""

    @property
    def client_id(self) -> str:
        return os.getenv(f"{self.code.upper()}_CLIENT_ID", "")

    @property
    def client_secret(self) -> str:
        return os.getenv(f"{self.code.upper()}_CLIENT_SECRET", "")

    @property
    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)


#: Пресеты популярных провайдеров. Endpoints — публичные и стабильные.
PRESETS: dict[str, OAuthProviderConfig] = {
    "google": OAuthProviderConfig(
        code="google",
        display_name="Google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scope="openid email profile",
        extra_authorize_params={"access_type": "online", "prompt": "select_account"},
    ),
    "microsoft": OAuthProviderConfig(
        code="microsoft",
        display_name="Microsoft",
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/oidc/userinfo",
        scope="openid email profile",
    ),
    "github": OAuthProviderConfig(
        code="github",
        display_name="GitHub",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
        emails_url="https://api.github.com/user/emails",
        scope="read:user user:email",
        subject_field="id",
        name_field="name",
    ),
}


def get_provider_config(code: str) -> OAuthProviderConfig | None:
    return PRESETS.get(code)


def enabled_providers() -> list[OAuthProviderConfig]:
    """Список провайдеров, у которых заданы client_id и client_secret."""
    return [c for c in PRESETS.values() if c.enabled]
