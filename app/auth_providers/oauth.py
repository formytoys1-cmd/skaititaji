"""OAuth 2.0 / OpenID Connect провайдер аутентификации.

Реализует authorization-code flow вручную (httpx, без внешних библиотек):
1. ``authorize_url(redirect_uri, state)`` — URL, куда отправить пользователя.
2. ``exchange(code, redirect_uri)`` — обмен кода на access-token и получение
   профиля (userinfo) → :class:`VerifiedIdentity`.

Секреты берутся из окружения через :class:`OAuthProviderConfig`; в тестах
HTTP замокан через ``httpx.MockTransport`` (реальная сеть не нужна).
"""
from __future__ import annotations

import logging
from urllib.parse import urlencode

import httpx

from app.auth_providers.base import AuthError, VerifiedIdentity
from app.oauth import OAuthProviderConfig, get_provider_config

logger = logging.getLogger("app.auth_providers.oauth")


class OAuthProvider:
    """Клиент одного OAuth/OIDC провайдера (google/microsoft/github)."""

    def __init__(self, config: OAuthProviderConfig,
                 client: httpx.Client | None = None) -> None:
        self.config = config
        self._client = client

    @classmethod
    def from_code(cls, code: str,
                  client: httpx.Client | None = None) -> "OAuthProvider":
        cfg = get_provider_config(code)
        if cfg is None:
            raise AuthError("error", f"Nezināms pakalpojums: {code}")
        if not cfg.enabled:
            raise AuthError("error", f"{cfg.display_name} nav konfigurēts")
        return cls(cfg, client=client)

    def _http(self) -> httpx.Client:
        return self._client or httpx.Client(timeout=20)

    def authorize_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.config.scope,
            "state": state,
            **self.config.extra_authorize_params,
        }
        return f"{self.config.authorize_url}?{urlencode(params)}"

    def exchange(self, code: str, redirect_uri: str) -> VerifiedIdentity:
        """Обменивает authorization code на токен и возвращает личность."""
        own = self._client is None
        client = self._http()
        try:
            token = self._fetch_token(client, code, redirect_uri)
            access_token = token.get("access_token")
            if not access_token:
                raise AuthError("error", "Nav piekļuves marķiera")
            profile = self._fetch_userinfo(client, access_token)
            return self._identity_from_profile(client, access_token, profile)
        except AuthError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning("OAuth exchange failed (%s): %s", self.config.code, e)
            raise AuthError("error", "Autentifikācija neizdevās") from e
        finally:
            if own:
                client.close()

    def _fetch_token(self, client: httpx.Client, code: str,
                     redirect_uri: str) -> dict:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        r = client.post(self.config.token_url, data=data,
                        headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()

    def _fetch_userinfo(self, client: httpx.Client, access_token: str) -> dict:
        r = client.get(
            self.config.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}",
                     "Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    def _identity_from_profile(self, client: httpx.Client, access_token: str,
                               profile: dict) -> VerifiedIdentity:
        cfg = self.config
        subject = profile.get(cfg.subject_field)
        if subject is None:
            raise AuthError("error", "Nav lietotāja identifikatora")
        email = profile.get(cfg.email_field)
        # GitHub может не отдавать e-mail в /user → берём основной из /user/emails.
        if not email and cfg.emails_url:
            email = self._github_primary_email(client, access_token)
        name = profile.get(cfg.name_field) or (email.split("@")[0] if email else "")
        return VerifiedIdentity(
            provider=cfg.code,
            subject=str(subject),
            full_name=name or "",
            email=(email.lower().strip() if email else None),
            extra={"raw_provider": cfg.code},
        )

    def _github_primary_email(self, client: httpx.Client,
                              access_token: str) -> str | None:
        try:
            r = client.get(
                self.config.emails_url,
                headers={"Authorization": f"Bearer {access_token}",
                         "Accept": "application/json"},
            )
            r.raise_for_status()
            emails = r.json()
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")), None
            )
            chosen = primary or next((e for e in emails if e.get("verified")), None)
            return chosen.get("email") if chosen else None
        except Exception:  # noqa: BLE001
            return None
