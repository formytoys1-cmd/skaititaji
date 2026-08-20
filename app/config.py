"""Настройки приложения. Все параметры читаются из окружения с разумными
значениями по умолчанию, чтобы демо запускалось без конфигурации."""
from __future__ import annotations

import os
import secrets
from functools import lru_cache

#: Небезопасный дефолт из старых версий. Остаётся только как маркер
#: «SECRET_KEY не задан» для boot-guard (SEC-002/SEC-004).
DEFAULT_SECRET_KEY = "dev-secret-change-me"


class Settings:
    """Глобальные настройки приложения."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "Skaitītāji")
        self.app_tagline: str = os.getenv(
            "APP_TAGLINE", "Ērta skaitītāju rādījumu nodošana"
        )
        self.database_url: str = os.getenv(
            "DATABASE_URL", "sqlite:///./data/skaititaji.db"
        )
        self.default_locale: str = os.getenv("DEFAULT_LOCALE", "lv")
        # SEC-002: DEBUG по умолчанию ВЫКЛЮЧЕН. Разработчик включает его явно.
        self.debug: bool = os.getenv("DEBUG", "0") == "1"

        # Признак боевого окружения. Определяется явными сигналами платформы
        # (Render) или переменной ENVIRONMENT, но НЕ выводится из DEBUG, чтобы
        # локальное демо работало предсказуемо.
        self.is_production: bool = self._detect_production()

        # SEC-002: секрет сессий. В dev при отсутствии ключа генерируем
        # случайный (сессии живут в пределах процесса — это безопасно и удобно).
        # В проде при отсутствии ключа оставляем маркер по умолчанию, чтобы
        # boot-guard (SEC-004) упал с понятным сообщением, а не работал на
        # предсказуемом секрете.
        self.secret_key, self.secret_key_is_default = self._resolve_secret_key()

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

    def _resolve_secret_key(self) -> tuple[str, bool]:
        """Возвращает (secret_key, is_default).

        - Задан непустой SECRET_KEY → используем его (is_default только если он
          буквально равен старому небезопасному дефолту).
        - Не задан и dev → генерируем случайный эфемерный ключ.
        - Не задан и прод → маркер по умолчанию (boot-guard упадёт).
        """
        env_secret = os.getenv("SECRET_KEY", "").strip()
        if env_secret:
            return env_secret, env_secret == DEFAULT_SECRET_KEY
        if not self.is_production:
            return secrets.token_urlsafe(48), False
        return DEFAULT_SECRET_KEY, True

    @property
    def demo_login_enabled(self) -> bool:
        """Доступен ли эндпоинт /demo-login: только в dev и вне прода."""
        return self.allow_demo_login and not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_production_config(cfg: "Settings | None" = None) -> None:
    """Boot-guard: в проде запрещает небезопасную конфигурацию (SEC-004).

    Ничего не делает вне прода. В проде собирает все проблемы и падает с
    единым понятным сообщением (RuntimeError), чтобы приложение не стартовало
    на небезопасных настройках.
    """
    cfg = cfg or settings
    if not cfg.is_production:
        return

    problems: list[str] = []
    if cfg.secret_key_is_default:
        problems.append(
            "SECRET_KEY не задан или равен небезопасному дефолту — "
            "задайте уникальный секрет в переменной окружения SECRET_KEY."
        )

    if problems:
        raise RuntimeError(
            "Небезопасная конфигурация для продакшена:\n- "
            + "\n- ".join(problems)
        )


settings = get_settings()
