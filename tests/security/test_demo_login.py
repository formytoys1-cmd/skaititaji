"""SEC-001 — GET /demo-login должен быть доступен только в dev, в проде → 404.

Reproduce → Fix → Verify → Guard: гостевой вход в один клик не должен
существовать на боевом сервере (обход аутентификации).
"""
import pytest

pytestmark = pytest.mark.security


def test_demo_login_disabled_in_prod(client, monkeypatch):
    from app.routers import auth as auth_router

    monkeypatch.setattr(auth_router.settings, "is_production", True)
    monkeypatch.setattr(auth_router.settings, "allow_demo_login", False)

    r = client.get("/demo-login?role=resident", follow_redirects=False)
    assert r.status_code == 404


def test_demo_login_enabled_in_dev(client, monkeypatch):
    from app.routers import auth as auth_router

    monkeypatch.setattr(auth_router.settings, "is_production", False)
    monkeypatch.setattr(auth_router.settings, "allow_demo_login", True)

    r = client.get("/demo-login?role=resident", follow_redirects=False)
    # В dev эндпоинт работает: редирект в кабинет роли (демо-аккаунт сидируется).
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/dzivoklis"
