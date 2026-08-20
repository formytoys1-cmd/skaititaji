"""Интеграционные тесты потока аутентификации (login/logout/guards).

Покрывают сессионные функции app/auth.py и роутер входа.
"""
import pytest

from app.models import UserRole

pytestmark = pytest.mark.integration


def test_login_success_redirects_to_role_home(client, session, factory):
    org = factory.organization()
    factory.user(organization=org, email="mgr@test.local",
                 password="pw-123456", role=UserRole.MANAGER)
    r = client.post("/login", data={"email": "mgr@test.local", "password": "pw-123456"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/parvalde"


def test_login_failure_redirects_back(client, factory):
    r = client.post("/login", data={"email": "nobody@test.local", "password": "x"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_protected_page_requires_auth(client):
    # /dzivoklis требует авторизации → 401 для анонима
    r = client.get("/dzivoklis")
    assert r.status_code == 401


def test_login_then_access_then_logout(client, session, factory):
    org = factory.organization()
    factory.user(organization=org, email="res@test.local",
                 password="pw-abcdef", role=UserRole.RESIDENT)
    # вход
    client.post("/login", data={"email": "res@test.local", "password": "pw-abcdef"})
    # доступ к своему кабинету
    r = client.get("/dzivoklis")
    assert r.status_code == 200
    # выход
    client.get("/logout")
    r2 = client.get("/dzivoklis")
    assert r2.status_code == 401


def test_role_guard_blocks_wrong_role(client, session, factory):
    # житель не должен попадать в админку (require_role SUPERADMIN → 403)
    org = factory.organization()
    factory.user(organization=org, email="res2@test.local",
                 password="pw-abcdef", role=UserRole.RESIDENT)
    client.post("/login", data={"email": "res2@test.local", "password": "pw-abcdef"})
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code in (403, 303)
