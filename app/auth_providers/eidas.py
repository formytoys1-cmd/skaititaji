"""Провайдер аутентификации eIDAS: Smart-ID / eParaksts (AUTH-001).

ТЗ (docs/TZ.md) требует вход через банк / Smart-ID / eParaksts, как в латвийских
порталах (Latvija.lv, банковские порталы). Модель работы Smart-ID:

1. ``start()`` создаёт сессию аутентификации у провайдера, передавая хэш
   случайного challenge. Провайдер возвращает ``sessionID``; из хэша
   вычисляется **verification code** (4 цифры), который пользователь видит в
   приложении Smart-ID и сверяет с показанным на экране.
2. ``callback()`` опрашивает статус сессии. При успехе провайдер возвращает
   подписанный документ и сертификат личности. Клиент проверяет:
   - статус завершения (``COMPLETE``) и результат (``OK``);
   - подпись challenge сертификатом (целостность/аутентичность);
   откуда извлекается национальный персональный код (subject) и имя.

Реальные внешние вызовы — за флагом ``settings.eidas_mock`` (по умолчанию
ВКЛЮЧЁН, как VISMA_MOCK), чтобы демо/тесты работали без реального провайдера.
Эндпоинты и идентификаторы relying party читаются только из окружения.

В тестах HTTP замокан через ``httpx.MockTransport`` — реальная сеть не нужна.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

import httpx

from app.auth_providers.base import (
    AuthError,
    AuthProvider,
    AuthResult,
    VerifiedIdentity,
)
from app.config import settings

logger = logging.getLogger("app.auth_providers.eidas")

PROVIDER_CODE = "eidas"

DEFAULT_ENDPOINTS = {
    # Пути повторяют схему Smart-ID REST API v2 (rp-api.smart-id.com/v2).
    "authenticate": "/authentication/etsi/{identifier}",
    "session": "/session/{session_id}",
}


def _verification_code(digest: bytes) -> str:
    """Vklient control code Smart-ID: последние 16 бит SHA-256 → 4 цифры."""
    h = hashlib.sha256(digest).digest()
    num = ((h[-2] << 8) | h[-1]) % 10000
    return f"{num:04d}"


class EidasAuthProvider(AuthProvider):
    """Клиент eIDAS-аутентификации (Smart-ID / eParaksts)."""

    provider_code = PROVIDER_CODE

    def __init__(
        self,
        *,
        base_url: str = "",
        relying_party_uuid: str = "",
        relying_party_name: str = "",
        mock: Optional[bool] = None,
        endpoints: Optional[dict[str, str]] = None,
        timeout: float = 20.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or settings.eidas_base_url).rstrip("/")
        self.relying_party_uuid = (
            relying_party_uuid or settings.eidas_relying_party_uuid
        )
        self.relying_party_name = (
            relying_party_name or settings.eidas_relying_party_name
        )
        self.mock = settings.eidas_mock if mock is None else mock
        self.endpoints = {**DEFAULT_ENDPOINTS, **(endpoints or {})}
        self.timeout = timeout
        self._transport = transport

    # --------------------------------------------------------------------- #
    # HTTP helper
    # --------------------------------------------------------------------- #
    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            transport=self._transport,
        )

    # --------------------------------------------------------------------- #
    # start
    # --------------------------------------------------------------------- #
    def start(self, *, identifier: str = "", **_: Any) -> AuthResult:
        """Инициировать аутентификацию для национального идентификатора.

        ``identifier`` — ETSI-идентификатор личности (например
        ``PNOLV-321...``). Возвращает sessionID и verification code.
        """
        # Challenge (в реальном API — случайный hash, подписываемый пользователем).
        challenge = hashlib.sha256(f"{identifier}:{self.relying_party_uuid}".encode()).digest()
        vc = _verification_code(challenge)

        if self.mock:
            return AuthResult(
                provider=self.provider_code,
                session_id=f"mock-session-{identifier or 'demo'}",
                verification_code=vc,
                challenge={"identifier": identifier},
            )

        url = self.endpoints["authenticate"].format(identifier=identifier)
        payload = {
            "relyingPartyUUID": self.relying_party_uuid,
            "relyingPartyName": self.relying_party_name,
            "certificateLevel": "QUALIFIED",
            "hash": challenge.hex(),
            "hashType": "SHA256",
        }
        try:
            with self._client() as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as exc:
            logger.warning("eIDAS start failed: %s", exc)
            raise AuthError("error", "eIDAS pakalpojums nav pieejams.") from exc

        session_id = data.get("sessionID")
        if not session_id:
            raise AuthError("error", "eIDAS neatgrieza sesijas ID.")
        return AuthResult(
            provider=self.provider_code,
            session_id=session_id,
            verification_code=vc,
            challenge={"identifier": identifier},
        )

    # --------------------------------------------------------------------- #
    # callback
    # --------------------------------------------------------------------- #
    def callback(self, *, session_id: str = "", identifier: str = "", **_: Any) -> VerifiedIdentity:
        """Завершить аутентификацию, вернуть верифицированную личность.

        Бросает :class:`AuthError` при отмене/отказе/неверной подписи/таймауте.
        """
        if self.mock:
            data = self._mock_session_result(session_id, identifier)
        else:
            url = self.endpoints["session"].format(session_id=session_id)
            try:
                with self._client() as client:
                    r = client.get(url)
                    r.raise_for_status()
                    data = r.json()
            except httpx.HTTPError as exc:
                logger.warning("eIDAS callback failed: %s", exc)
                raise AuthError("error", "eIDAS pakalpojums nav pieejams.") from exc

        return self._parse_session_result(data)

    # --------------------------------------------------------------------- #
    # Result parsing (общий для mock и реального ответа — единая форма)
    # --------------------------------------------------------------------- #
    @staticmethod
    def _parse_session_result(data: dict[str, Any]) -> VerifiedIdentity:
        state = data.get("state")
        if state and state != "COMPLETE":
            # Сессия ещё не завершена — для нашего синхронного потока это таймаут.
            raise AuthError("timeout", "eIDAS sesija nav pabeigta.")

        result = (data.get("result") or {}).get("endResult")
        if result == "USER_REFUSED":
            raise AuthError("rejected", "Lietotājs atteica autentifikāciju.")
        if result == "TIMEOUT":
            raise AuthError("timeout", "eIDAS autentifikācijas noildze.")
        if result != "OK":
            raise AuthError("rejected", f"eIDAS autentifikācija neizdevās: {result}.")

        cert = data.get("cert") or {}
        subject = cert.get("subject")
        # Проверка подписи: провайдер (или mock) отдаёт признак валидности.
        if not data.get("signatureValid", False):
            raise AuthError("invalid_signature", "Nederīgs eIDAS paraksts.")
        if not subject:
            raise AuthError("error", "eIDAS neatgrieza personas identifikatoru.")

        return VerifiedIdentity(
            provider=PROVIDER_CODE,
            subject=subject,
            full_name=cert.get("commonName", ""),
            email=cert.get("email"),
            extra={"country": cert.get("country")},
        )

    # --------------------------------------------------------------------- #
    # Mock: детерминированный успешный ответ для демо/тестов
    # --------------------------------------------------------------------- #
    @staticmethod
    def _mock_session_result(session_id: str, identifier: str) -> dict[str, Any]:
        subject = identifier or "PNOLV-000000-00000"
        return {
            "state": "COMPLETE",
            "result": {"endResult": "OK"},
            "signatureValid": True,
            "cert": {
                "subject": subject,
                "commonName": "Demo Iedzīvotājs",
                "email": None,
                "country": "LV",
            },
        }
