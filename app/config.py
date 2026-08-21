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

        # AUTH-001: eIDAS-аутентификация (Smart-ID / eParaksts).
        # ТЗ требует вход через банк / Smart-ID / eParaksts, как в латвийских
        # порталах. Реальные вызовы внешнего провайдера — за флагом EIDAS_MOCK,
        # который по умолчанию ВКЛЮЧЁН (mock), чтобы демо и тесты работали без
        # реального провайдера (как сделано для Visma). Эндпоинты/секреты —
        # только из окружения.
        self.eidas_mock: bool = os.getenv("EIDAS_MOCK", "1") == "1"
        self.eidas_base_url: str = os.getenv("EIDAS_BASE_URL", "")
        self.eidas_relying_party_uuid: str = os.getenv(
            "EIDAS_RELYING_PARTY_UUID", ""
        )
        self.eidas_relying_party_name: str = os.getenv(
            "EIDAS_RELYING_PARTY_NAME", ""
        )

        # Публичный базовый URL (для ссылок в письмах верификации). На Render
        # берётся из RENDER_EXTERNAL_URL; локально — http://127.0.0.1:8000.
        self.public_base_url: str = (
            os.getenv("PUBLIC_BASE_URL")
            or os.getenv("RENDER_EXTERNAL_URL")
            or os.getenv("SELF_PING_URL")
            or "http://127.0.0.1:8000"
        ).rstrip("/")

        # Отправка почты (верификация e-mail). Free-режим: если SMTP не настроен,
        # письма пишутся в data/outbox/ и лог (для демо), без внешних сервисов.
        self.email_host: str = os.getenv("EMAIL_HOST", "")
        self.email_port: int = int(os.getenv("EMAIL_PORT", "587") or "587")
        self.email_user: str = os.getenv("EMAIL_USER", "")
        self.email_password: str = os.getenv("EMAIL_PASSWORD", "")
        self.email_from: str = os.getenv(
            "EMAIL_FROM", self.email_user or "no-reply@skaititaji.local"
        )
        self.email_use_tls: bool = os.getenv("EMAIL_USE_TLS", "1") == "1"

        # Требовать подтверждение e-mail перед входом (email+пароль).
        # По умолчанию включено вне тестов; тесты могут отключать через env.
        self.require_email_verification: bool = (
            os.getenv("REQUIRE_EMAIL_VERIFICATION", "1") == "1"
        )
        # Сколько человек может зарегистрироваться на одну квартиру по умолчанию
        # (запас ×2, чтобы 2 жильца могли подавать показания).
        self.default_unit_capacity: int = int(
            os.getenv("DEFAULT_UNIT_CAPACITY", "2") or "2"
        )

    @property
    def email_configured(self) -> bool:
        """Настроен ли реальный SMTP (иначе используется outbox-фоллбек)."""
        return bool(self.email_host and self.email_from)

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
    if cfg.debug:
        problems.append(
            "DEBUG включён в проде — отключите его (DEBUG=0)."
        )
    if cfg.database_url.strip().lower().startswith("sqlite"):
        problems.append(
            "DATABASE_URL указывает на sqlite — используйте полноценную СУБД "
            "(например, PostgreSQL) в проде."
        )
    if cfg.allow_demo_login:
        problems.append(
            "ALLOW_DEMO_LOGIN включён в проде — гостевой вход обходит "
            "аутентификацию, выключите его (ALLOW_DEMO_LOGIN=0)."
        )
    # SEC-003: без ключа шифрования секреты интеграций легли бы на эфемерный
    # ключ (не переживает рестарт и не задан оператором) — в проде это ошибка.
    if not os.getenv("SECRETS_ENCRYPTION_KEY", "").strip():
        problems.append(
            "SECRETS_ENCRYPTION_KEY не задан — секреты интеграций (пароль Visma) "
            "не могут быть надёжно зашифрованы at-rest; задайте ключ в окружении."
        )

    if problems:
        raise RuntimeError(
            "Небезопасная конфигурация для продакшена:\n- "
            + "\n- ".join(problems)
        )


settings = get_settings()
