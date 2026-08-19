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

        # Интеграция с Visma Horizon REST API.
        # По умолчанию используется mock-режим, чтобы демо работало без реального сервера.
        self.visma_base_url: str = os.getenv("VISMA_BASE_URL", "")
        self.visma_username: str = os.getenv("VISMA_USERNAME", "")
        self.visma_password: str = os.getenv("VISMA_PASSWORD", "")
        self.visma_mock: bool = os.getenv("VISMA_MOCK", "1") == "1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
