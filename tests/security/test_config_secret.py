"""SEC-002 — небезопасные дефолты конфигурации.

Дефолтный SECRET_KEY «dev-secret-change-me» и DEBUG=1 по умолчанию — опасны
для прода. Требования:
- DEBUG по умолчанию выключен (0);
- в dev при отсутствии SECRET_KEY генерируется случайный ключ (не дефолт);
- в проде дефолтный/отсутствующий SECRET_KEY приводит к падению boot-guard.
"""
import pytest

pytestmark = pytest.mark.security


def _fresh_settings(monkeypatch, **env):
    from app.config import Settings

    for key in ("SECRET_KEY", "DEBUG", "ENVIRONMENT", "ENV",
                "RENDER_EXTERNAL_URL", "SELF_PING_URL", "ALLOW_DEMO_LOGIN",
                "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings()


def test_debug_off_by_default(monkeypatch):
    s = _fresh_settings(monkeypatch)
    assert s.debug is False


def test_dev_generates_random_secret_when_unset(monkeypatch):
    # dev-режим, SECRET_KEY не задан → генерируется случайный (не дефолтный) ключ
    s = _fresh_settings(monkeypatch, ENVIRONMENT="development")
    assert s.secret_key != "dev-secret-change-me"
    assert s.secret_key_is_default is False
    assert len(s.secret_key) >= 16


def test_boot_fails_on_default_secret_in_prod(monkeypatch):
    from app.config import validate_production_config

    # Прод с валидной БД и выключенным demo-login, но без SECRET_KEY →
    # используется дефолтный маркер, boot-guard обязан упасть.
    s = _fresh_settings(
        monkeypatch,
        ENVIRONMENT="production",
        DEBUG="0",
        DATABASE_URL="postgresql://u:p@db/app",
        ALLOW_DEMO_LOGIN="0",
    )
    assert s.is_production is True
    assert s.secret_key_is_default is True
    with pytest.raises(RuntimeError) as exc:
        validate_production_config(s)
    assert "SECRET_KEY" in str(exc.value)
