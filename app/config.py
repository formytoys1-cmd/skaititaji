"""Настройки приложения. Все параметры читаются из окружения с разумными
значениями по умолчанию, чтобы демо запускалось без конфигурации."""
from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """Глобальные настройки приложения."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "Skaitītāji")
        self.app_tagline: str = os.getenv(
            "APP_TAGLINE", "Ērta skaitītāju rādījumu nodošana"
        )
        self.secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
        self.database_url: str = os.getenv(
            "DATABASE_URL", "sqlite:///./data/skaititaji.db"
        )
        self.default_locale: str = os.getenv("DEFAULT_LOCALE", "lv")
        self.debug: bool = os.getenv("DEBUG", "1") == "1"

        # Признак боевого окружения. Определяется явными сигналами платформы
        # (Render) или переменной ENVIRONMENT, но НЕ выводится из DEBUG, чтобы
        # локальное демо работало предсказуемо.
        self.is_production: bool = self._detect_production()

        # Гостевой вход в один клик (demo-login) — только для разработки/демо.
        # В проде по умолчанию выключен (см. SEC-001/SEC-004).
        self.allow_demo_login: bool = (
            os.getenv("ALLOW_DEMO_LOGIN", "1" if self.debug else "0") == "1"
        )

        # Ключ для защищённого API агента (удалённое чтение/ответы в консоли
        # обратной связи). Если пустой — эндпоинты /agent/api отключены.
        self.agent_api_key: str = os.getenv("AGENT_API_KEY", "")

        # Интеграция с Visma Horizon REST API.
        # По умолчанию используется mock-режим, чтобы демо работало без реального сервера.
        self.visma_base_url: str = os.getenv("VISMA_BASE_URL", "")
        self.visma_username: str = os.getenv("VISMA_USERNAME", "")
        self.visma_password: str = os.getenv("VISMA_PASSWORD", "")
        self.visma_mock: bool = os.getenv("VISMA_MOCK", "1") == "1"

    @staticmethod
    def _detect_production() -> bool:
        """Боевое окружение по явным сигналам, не по DEBUG.

        Прод определяется переменной ENVIRONMENT/ENV (prod/production) или
        наличием платформенных переменных Render. Локально ни одна из них не
        задана, поэтому демо всегда стартует в dev-режиме.
        """
        env = os.getenv("ENVIRONMENT", os.getenv("ENV", "")).strip().lower()
        if env in {"prod", "production"}:
            return True
        if env in {"dev", "development", "local", "test"}:
            return False
        return bool(os.getenv("RENDER_EXTERNAL_URL") or os.getenv("SELF_PING_URL"))

    @property
    def demo_login_enabled(self) -> bool:
        """Доступен ли эндпоинт /demo-login: только в dev и вне прода."""
        return self.allow_demo_login and not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
