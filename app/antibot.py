"""Защита форм от ботов (без внешних сервисов, free).

Три бесплатных слоя (в дополнение к CSRF и rate-limit):
1. **Honeypot** — скрытое поле, которое человек не видит и не заполняет; боты,
   заполняющие все поля, себя выдают.
2. **Time-trap** — в форму кладётся подписанная (HMAC) метка времени рендера.
   Если форма отправлена подозрительно быстро (< MIN_SECONDS) или метка
   поддельная/протухла — это бот.
3. (Опц.) Cloudflare Turnstile — включается переменной окружения, если понадобится
   более сильная защита; по умолчанию выключен, чтобы оставаться на free.

Подпись метки времени привязана к SECRET_KEY, поэтому её нельзя подделать без
знания секрета.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from app.config import settings

#: Имя honeypot-поля (нейтральное, чтобы автозаполнение ботов сработало).
HONEYPOT_FIELD = "company"
#: Имя поля с подписанной меткой времени.
TIMESTAMP_FIELD = "form_ts"
#: Минимальное «человеческое» время заполнения формы, сек.
MIN_SECONDS = 2.0
#: Максимальный возраст формы, сек (защита от повторного использования).
MAX_SECONDS = 3600.0


def _sign(value: str) -> str:
    mac = hmac.new(
        settings.secret_key.encode(), value.encode(), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


def make_timestamp_token(now: float | None = None) -> str:
    """Подписанная метка времени для вставки в форму (скрытое поле)."""
    ts = str(int(now if now is not None else time.time()))
    return f"{ts}.{_sign(ts)}"


def _valid_timestamp(token: str, now: float | None = None) -> bool:
    try:
        ts_str, sig = token.split(".", 1)
    except ValueError:
        return False
    if not hmac.compare_digest(sig, _sign(ts_str)):
        return False
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    now = now if now is not None else time.time()
    age = now - ts
    return MIN_SECONDS <= age <= MAX_SECONDS


def check_human(honeypot: str | None, timestamp_token: str | None,
                now: float | None = None) -> bool:
    """True, если запрос похож на человеческий; False — если на бота.

    - honeypot должен быть пустым;
    - метка времени должна быть валидной и в допустимом окне.
    """
    if honeypot:
        return False
    if not timestamp_token or not _valid_timestamp(timestamp_token, now=now):
        return False
    return True
