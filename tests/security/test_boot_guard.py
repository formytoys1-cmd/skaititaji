"""SEC-004 — boot-guard validate_production_config().

В проде приложение не должно стартовать на небезопасной конфигурации:
- дефолтный/отсутствующий SECRET_KEY;
- DEBUG включён;
- DATABASE_URL указывает на sqlite (эфемерная/файловая БД);
- ALLOW_DEMO_LOGIN включён.
Все проблемы собираются и репортятся понятным сообщением.
"""
import pytest

pytestmark = pytest.mark.security

_PROD_ENV = {
    "ENVIRONMENT": "production",
    "SECRET_KEY": "a-strong-unique-production-secret-value",
    "DEBUG": "0",
    "DATABASE_URL": "postgresql://u:p@db/app",
    "ALLOW_DEMO_LOGIN": "0",
}


def _settings(monkeypatch, **overrides):
    from app.config import Settings

    for key in ("SECRET_KEY", "DEBUG", "ENVIRONMENT", "ENV",
                "RENDER_EXTERNAL_URL", "SELF_PING_URL", "ALLOW_DEMO_LOGIN",
                "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    env = {**_PROD_ENV, **overrides}
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return Settings()


def test_production_config_validation(monkeypatch):
    from app.config import validate_production_config

    # 1) Полностью валидная боевая конфигурация — не падает.
    validate_production_config(_settings(monkeypatch))

    # 2) Отсутствующий SECRET_KEY → падение с упоминанием SECRET_KEY.
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_config(_settings(monkeypatch, SECRET_KEY=None))

    # 3) DEBUG включён в проде → падение.
    with pytest.raises(RuntimeError, match="DEBUG"):
        validate_production_config(_settings(monkeypatch, DEBUG="1"))

    # 4) sqlite в проде → падение.
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_config(
            _settings(monkeypatch, DATABASE_URL="sqlite:///./data/x.db")
        )

    # 5) demo-login включён в проде → падение.
    with pytest.raises(RuntimeError, match="ALLOW_DEMO_LOGIN"):
        validate_production_config(_settings(monkeypatch, ALLOW_DEMO_LOGIN="1"))


def test_validation_is_noop_outside_prod(monkeypatch):
    from app.config import validate_production_config

    # В dev даже «плохая» конфигурация не роняет приложение.
    s = _settings(monkeypatch, ENVIRONMENT="development",
                  SECRET_KEY=None, DEBUG="1",
                  DATABASE_URL="sqlite:///./data/x.db", ALLOW_DEMO_LOGIN="1")
    assert s.is_production is False
    validate_production_config(s)  # не бросает
