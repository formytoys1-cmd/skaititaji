"""Rate-limiting и анти-enumeration для аутентификации (SEC-006).

Мотивация: без ограничения частоты POST /login, POST /registreties и
GET /demo-login открыты для брутфорса паролей и перебора существующих
аккаунтов (enumeration). Здесь — простой in-memory лимитер со скользящим
окном и экспоненциальной задержкой, а также единый «неверный логин/пароль»
без раскрытия существования email (это обеспечивается на уровне роутера).

Хранилище — процессная память: для одного инстанса (демо/Render free) этого
достаточно. При масштабировании на несколько инстансов сюда подключается общий
backend (Redis) без изменения интерфейса.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from fastapi import Request

# Значения по умолчанию можно переопределить из окружения (см. app/config при
# необходимости); здесь заданы разумные пороги для аутентификации.
DEFAULT_MAX_ATTEMPTS = 5          # попыток за окно до блокировки
DEFAULT_WINDOW_SECONDS = 300.0    # длина скользящего окна (5 минут)
DEFAULT_BASE_DELAY = 0.0          # база экспоненциальной задержки (сек)


@dataclass
class _Bucket:
    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """Скользящее окно попыток по строковому ключу (например, IP+email)."""

    def __init__(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        base_delay: float = DEFAULT_BASE_DELAY,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.base_delay = base_delay
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _prune(self, bucket: _Bucket, now: float) -> None:
        cutoff = now - self.window_seconds
        bucket.timestamps = [t for t in bucket.timestamps if t >= cutoff]

    def hit(self, key: str) -> tuple[bool, float]:
        """Регистрирует попытку. Возвращает (allowed, retry_after_seconds).

        Если попыток в окне больше лимита — allowed=False и время до
        разблокировки (по самой старой попытке в окне).
        """
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.setdefault(key, _Bucket())
            self._prune(bucket, now)
            bucket.timestamps.append(now)
            count = len(bucket.timestamps)
            if count > self.max_attempts:
                oldest = bucket.timestamps[0]
                retry_after = max(0.0, self.window_seconds - (now - oldest))
                return False, retry_after
            return True, 0.0

    def delay_for(self, key: str) -> float:
        """Экспоненциальная задержка по числу попыток в окне (анти-брутфорс)."""
        if self.base_delay <= 0:
            return 0.0
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if not bucket:
                return 0.0
            self._prune(bucket, now)
            n = max(0, len(bucket.timestamps) - 1)
        return self.base_delay * (2 ** n)

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()


def client_ip(request: Request) -> str:
    """IP клиента с учётом обратного прокси (Render проставляет XFF)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


#: Общий лимитер аутентификации на процесс.
auth_limiter = RateLimiter()
