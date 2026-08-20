"""Интеграционные тесты eIDAS-входа (AUTH-001) через HTTP-роуты.

Mock-режим включён по умолчанию, поэтому реальная сеть не нужна.
"""
import pytest

from tests.conftest import csrf_token

pytestmark = pytest.mark.integration


def test_eidas_login_form_renders(client):
    r = client.get("/eidas/login")
    assert r.status_code == 200
    assert "Smart-ID" in r.text


def test_eidas_unknown_identity_redirects_to_register(client):
    r = client.post(
        "/eidas/login",
        data={"identifier": "PNOLV-999999-99999", "csrf_token": csrf_token(client)},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/registreties"


def test_eidas_known_identity_logs_in(client, app_on_test_db):
    """Пользователь с привязанным external_subject входит через eIDAS."""
    from sqlmodel import Session, select

    from app.database import engine
    from app.models import User

    ident = "PNOLV-321054-12345"
    with Session(engine) as s:
        user = s.exec(select(User).where(User.email == "resident@demo.lv")).first()
        user.external_provider = "eidas"
        user.external_subject = ident
        s.add(user)
        s.commit()

    r = client.post(
        "/eidas/login",
        data={"identifier": ident, "csrf_token": csrf_token(client)},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/dzivoklis"
