"""Интеграция: самрегистрация → подтверждение e-mail → вход, вместимость,
анти-бот. Персональные данные синтетические (фабрики)."""
import time

import pytest
from sqlmodel import Session, select

from app.antibot import make_timestamp_token
from app.models import EmailVerification, User

pytestmark = pytest.mark.integration


def _human_ts():
    """Метка времени, как у человека (форма заполнялась > MIN_SECONDS)."""
    return make_timestamp_token(now=time.time() - 5)


def _register(client, csrf, account_number, email, *, company="", ts=None):
    return client.post(
        "/registreties",
        data={
            "full_name": "Test Resident",
            "email": email,
            "password": "sup3rpass",
            "account_number": account_number,
            "company": company,
            "form_ts": ts if ts is not None else _human_ts(),
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )


def _make_unit(factory, **unit_kw):
    org = factory.organization()
    b = factory.building(org)
    u = factory.unit(b, **unit_kw)
    return org, b, u


def test_register_and_resend_forms_render(client):
    # GET-страницы должны рендериться (ловит ошибки контекста render()).
    assert client.get("/registreties").status_code == 200
    assert client.get("/verificet/atkartot").status_code == 200
    assert client.get("/registreties/parbaudiet").status_code == 200
    # honeypot-поле и метка времени присутствуют в форме
    html = client.get("/registreties").text
    assert 'name="company"' in html
    assert 'name="form_ts"' in html


def test_full_registration_and_verification(client, factory, engine, csrf):
    org, b, u = _make_unit(factory, account_number="ACC-REG-1", max_residents=2)

    r = _register(client, csrf, "ACC-REG-1", "newuser@test.local")
    assert r.status_code == 200
    assert "/verificet?token=" in r.text  # в free-режиме ссылка показана на экране

    with Session(engine) as s:
        user = s.exec(select(User).where(User.email == "newuser@test.local")).first()
        assert user is not None and user.is_verified is False
        ev = s.exec(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        ).first()
        assert ev is not None
        token = ev.token

    # переход по ссылке из письма подтверждает и логинит
    rv = client.get(f"/verificet?token={token}", follow_redirects=False)
    assert rv.status_code == 303
    assert rv.headers["location"] == "/dzivoklis"

    with Session(engine) as s:
        user = s.exec(select(User).where(User.email == "newuser@test.local")).first()
        assert user.is_verified is True and user.verified_at is not None


def test_unverified_login_blocked(client, factory, engine, csrf):
    _make_unit(factory, account_number="ACC-REG-2", max_residents=2)
    _register(client, csrf, "ACC-REG-2", "pending@test.local")

    # без подтверждения вход не пускает, ведёт на повторную отправку
    r = client.post(
        "/login",
        data={"email": "pending@test.local", "password": "sup3rpass",
              "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/verificet/atkartot"


def test_capacity_enforced(client, factory, engine, csrf):
    org, b, u = _make_unit(factory, account_number="ACC-CAP-1", max_residents=1)
    # квартира уже заполнена (1 житель)
    factory.resident_of(u, organization=org, email="first@test.local")

    r = _register(client, csrf, "ACC-CAP-1", "second@test.local")
    assert r.status_code == 303
    assert r.headers["location"] == "/registreties"
    with Session(engine) as s:
        assert s.exec(
            select(User).where(User.email == "second@test.local")
        ).first() is None


def test_honeypot_blocks_bot(client, factory, engine, csrf):
    _make_unit(factory, account_number="ACC-BOT-1", max_residents=2)
    r = _register(client, csrf, "ACC-BOT-1", "bot@test.local", company="filled")
    assert r.status_code == 303
    assert r.headers["location"] == "/registreties"
    with Session(engine) as s:
        assert s.exec(
            select(User).where(User.email == "bot@test.local")
        ).first() is None


def test_too_fast_submit_blocked(client, factory, engine, csrf):
    _make_unit(factory, account_number="ACC-FAST-1", max_residents=2)
    fresh = make_timestamp_token()  # возраст ~0 → бот
    r = _register(client, csrf, "ACC-FAST-1", "fast@test.local", ts=fresh)
    assert r.status_code == 303
    assert r.headers["location"] == "/registreties"
    with Session(engine) as s:
        assert s.exec(
            select(User).where(User.email == "fast@test.local")
        ).first() is None


def test_resend_creates_new_token(client, factory, engine, csrf):
    _make_unit(factory, account_number="ACC-RES-1", max_residents=2)
    _register(client, csrf, "ACC-RES-1", "resend@test.local")

    with Session(engine) as s:
        user = s.exec(
            select(User).where(User.email == "resend@test.local")
        ).first()
        before = len(s.exec(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        ).all())

    r = client.post(
        "/verificet/atkartot",
        data={"email": "resend@test.local", "company": "",
              "form_ts": _human_ts(), "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    with Session(engine) as s:
        after = len(s.exec(
            select(EmailVerification).where(EmailVerification.user_id == user.id)
        ).all())
    assert after == before + 1
