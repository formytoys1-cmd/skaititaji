"""Интеграция OAuth: login-redirect, callback (существующий/новый юзер),
проверка state, завершение регистрации с привязкой к квартире."""
from urllib.parse import parse_qs, urlparse

import pytest
from sqlmodel import Session, select

from app.auth_providers.base import VerifiedIdentity
from app.models import UnitResident, User, UserRole

pytestmark = pytest.mark.integration


@pytest.fixture()
def google_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")


def _state_from_login(client):
    r = client.get("/auth/google/login", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/")
    q = parse_qs(urlparse(loc).query)
    return q["state"][0]


def _patch_exchange(monkeypatch, identity):
    from app.auth_providers.oauth import OAuthProvider
    monkeypatch.setattr(OAuthProvider, "exchange",
                        lambda self, code, redirect_uri: identity)


def test_login_redirects_to_provider(client, google_env):
    r = client.get("/auth/google/login", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith(
        "https://accounts.google.com/o/oauth2/v2/auth?")


def test_callback_existing_user_logs_in(client, google_env, factory, engine, monkeypatch):
    org = factory.organization()
    # существующий аккаунт с тем же email
    factory.user(organization=org, email="known@gmail.com", role=UserRole.RESIDENT)

    _patch_exchange(monkeypatch, VerifiedIdentity(
        provider="google", subject="g-1", full_name="Known", email="known@gmail.com"))

    state = _state_from_login(client)
    r = client.get(f"/auth/google/callback?code=abc&state={state}",
                   follow_redirects=False)
    assert r.status_code == 303
    # вошёл (не на /login)
    assert r.headers["location"] != "/login"
    with Session(engine) as s:
        u = s.exec(select(User).where(User.email == "known@gmail.com")).first()
        assert u.external_provider == "google" and u.external_subject == "g-1"


def test_callback_bad_state_rejected(client, google_env, monkeypatch):
    _patch_exchange(monkeypatch, VerifiedIdentity(
        provider="google", subject="g-2", email="x@gmail.com"))
    # правильный state в сессии, но присылаем неверный
    _state_from_login(client)
    r = client.get("/auth/google/callback?code=abc&state=WRONG",
                   follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_callback_new_user_completes_registration(
        client, google_env, factory, engine, monkeypatch):
    org = factory.organization()
    b = factory.building(org)
    u = factory.unit(b, account_number="OAUTH-ACC-1", max_residents=2)

    _patch_exchange(monkeypatch, VerifiedIdentity(
        provider="google", subject="g-new", full_name="Fresh User",
        email="fresh@gmail.com"))

    state = _state_from_login(client)
    r = client.get(f"/auth/google/callback?code=abc&state={state}",
                   follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/registreties/pabeigt"

    # завершаем регистрацию: только account_number
    form = client.get("/registreties/pabeigt")
    assert form.status_code == 200
    import re
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', form.text).group(1)
    r2 = client.post("/registreties/pabeigt",
                     data={"account_number": "OAUTH-ACC-1", "csrf_token": csrf},
                     follow_redirects=False)
    assert r2.status_code == 303
    assert r2.headers["location"] == "/dzivoklis"

    with Session(engine) as s:
        user = s.exec(select(User).where(User.email == "fresh@gmail.com")).first()
        assert user is not None
        assert user.is_verified is True
        assert user.external_provider == "google"
        link = s.exec(
            select(UnitResident).where(UnitResident.user_id == user.id)
        ).first()
        assert link is not None and link.unit_id == u.id


def test_login_page_shows_google_button(client, google_env):
    html = client.get("/login").text
    assert "/auth/google/login" in html
