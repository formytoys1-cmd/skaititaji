"""Контрактные тесты провайдера eIDAS (Smart-ID / eParaksts) — AUTH-001.

Все HTTP-вызовы замоканы через ``httpx.MockTransport`` — реальная сеть НЕ
используется. Проверяем разбор ответов провайдера: успешная аутентификация,
отказ/отмена пользователя, неверная подпись. Также проверяем, что локальный
вход (email+пароль) продолжает работать через ту же абстракцию.
"""
from __future__ import annotations

import httpx
import pytest

from app.auth_providers.base import AuthError, VerifiedIdentity, resolve_user
from app.auth_providers.eidas import EidasAuthProvider
from app.auth_providers.local import LocalAuthProvider
from app.auth_providers.registry import get_auth_provider

BASE_URL = "https://rp-api.eidas.example.lv/v2"
IDENTIFIER = "PNOLV-321054-12345"


def _provider(handler) -> EidasAuthProvider:
    transport = httpx.MockTransport(handler)
    return EidasAuthProvider(
        base_url=BASE_URL,
        relying_party_uuid="rp-uuid",
        relying_party_name="Skaititaji",
        mock=False,
        transport=transport,
    )


# --------------------------------------------------------------------------- #
# Форма ответов провайдера (по схеме Smart-ID REST v2).
# --------------------------------------------------------------------------- #
def _session_ok() -> dict:
    return {
        "state": "COMPLETE",
        "result": {"endResult": "OK"},
        "signatureValid": True,
        "cert": {
            "subject": IDENTIFIER,
            "commonName": "Jānis Bērziņš",
            "email": "janis@example.lv",
            "country": "LV",
        },
    }


def test_eidas_login_success():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(f"/authentication/etsi/{IDENTIFIER}"):
            return httpx.Response(200, json={"sessionID": "sess-1"})
        return httpx.Response(200, json=_session_ok())

    prov = _provider(handler)
    started = prov.start(identifier=IDENTIFIER)
    assert started.session_id == "sess-1"
    assert len(started.verification_code) == 4

    identity = prov.callback(session_id=started.session_id, identifier=IDENTIFIER)
    assert isinstance(identity, VerifiedIdentity)
    assert identity.provider == "eidas"
    assert identity.subject == IDENTIFIER
    assert identity.full_name == "Jānis Bērziņš"
    assert identity.email == "janis@example.lv"


def test_eidas_login_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "state": "COMPLETE",
                "result": {"endResult": "USER_REFUSED"},
                "signatureValid": False,
                "cert": {},
            },
        )

    prov = _provider(handler)
    with pytest.raises(AuthError) as exc:
        prov.callback(session_id="sess-x", identifier=IDENTIFIER)
    assert exc.value.reason == "rejected"


def test_eidas_login_invalid_signature():
    def handler(request: httpx.Request) -> httpx.Response:
        data = _session_ok()
        data["signatureValid"] = False
        return httpx.Response(200, json=data)

    prov = _provider(handler)
    with pytest.raises(AuthError) as exc:
        prov.callback(session_id="sess-x", identifier=IDENTIFIER)
    assert exc.value.reason == "invalid_signature"


def test_eidas_login_timeout_when_not_complete():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"state": "RUNNING"})

    prov = _provider(handler)
    with pytest.raises(AuthError) as exc:
        prov.callback(session_id="sess-x", identifier=IDENTIFIER)
    assert exc.value.reason == "timeout"


def test_eidas_mock_mode_default_no_network():
    """В mock-режиме (дефолт) вход работает без транспорта/сети."""
    prov = EidasAuthProvider(mock=True)
    started = prov.start(identifier=IDENTIFIER)
    identity = prov.callback(session_id=started.session_id, identifier=IDENTIFIER)
    assert identity.subject == IDENTIFIER
    assert identity.provider == "eidas"


# --------------------------------------------------------------------------- #
# Обратная совместимость: локальный вход через ту же абстракцию.
# --------------------------------------------------------------------------- #
def test_local_login_still_works(session, factory):
    factory.user(email="resident@example.lv", password="secret123")
    prov = LocalAuthProvider(session)
    identity = prov.callback(email="resident@example.lv", password="secret123")
    assert identity.provider == "local"
    assert identity.email == "resident@example.lv"


def test_local_login_wrong_password_rejected(session, factory):
    factory.user(email="resident@example.lv", password="secret123")
    prov = LocalAuthProvider(session)
    with pytest.raises(AuthError) as exc:
        prov.callback(email="resident@example.lv", password="wrong")
    assert exc.value.reason == "rejected"


# --------------------------------------------------------------------------- #
# Маппинг верифицированной личности на пользователя.
# --------------------------------------------------------------------------- #
def test_resolve_user_links_by_email_then_subject(session, factory):
    user = factory.user(email="janis@example.lv", password="secret123")
    identity = VerifiedIdentity(
        provider="eidas", subject=IDENTIFIER, full_name="Jānis", email="janis@example.lv"
    )
    resolved = resolve_user(session, identity)
    assert resolved is not None and resolved.id == user.id
    # После первого входа субъект привязан — повторный поиск идёт по subject.
    assert resolved.external_provider == "eidas"
    assert resolved.external_subject == IDENTIFIER

    identity2 = VerifiedIdentity(provider="eidas", subject=IDENTIFIER)
    assert resolve_user(session, identity2).id == user.id


def test_resolve_user_none_when_unknown(session):
    identity = VerifiedIdentity(provider="eidas", subject="PNOLV-999", email=None)
    assert resolve_user(session, identity) is None


def test_registry_returns_providers(session):
    assert isinstance(get_auth_provider("local", session), LocalAuthProvider)
    assert isinstance(get_auth_provider("eidas"), EidasAuthProvider)
    with pytest.raises(ValueError):
        get_auth_provider("unknown")
