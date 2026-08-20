"""Шифрование секретов интеграций at-rest (SEC-003).

Пароли/токены доступа к внешним системам (например, Visma Horizon) не должны
лежать в БД открытым текстом. Здесь — симметричное аутентифицированное
шифрование на стандартной библиотеке (без внешних зависимостей, в духе
app/auth.py, где PBKDF2 берётся из hashlib).

Схема (authenticated encryption, encrypt-then-MAC):
- из мастер-ключа окружения выводятся два подключа (enc/mac) через HKDF-SHA256;
- поток шифра — HMAC-SHA256 в режиме счётчика (keystream), XOR с открытым
  текстом; так мы получаем потоковый шифр без сторонних AES-реализаций;
- целостность защищает HMAC-SHA256 по (nonce || ciphertext), проверяется в
  постоянном по времени сравнении до расшифровки.

Ключ берётся ТОЛЬКО из окружения (SECRETS_ENCRYPTION_KEY). Дефолта-секрета в
коде нет. В dev при отсутствии ключа генерируется эфемерный ключ на процесс —
приложение не падает, но такие секреты не переживают перезапуск (что приемлемо
для локального демо в mock-режиме); в проде отсутствие ключа выявляет boot-guard.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

_ENV_KEY = "SECRETS_ENCRYPTION_KEY"
_PREFIX = "enc:v1:"
_NONCE_LEN = 16
_MAC_LEN = 32

#: Эфемерный ключ для dev (генерируется один раз на процесс, если ключ не задан
#: в окружении). Никогда не используется в проде — там boot-guard требует явный.
_EPHEMERAL_KEY = secrets.token_bytes(32)


def _master_key() -> bytes:
    raw = os.getenv(_ENV_KEY, "").strip()
    if raw:
        # Принимаем как base64/urlsafe, так и произвольную строку.
        try:
            decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            if len(decoded) >= 32:
                return decoded[:32]
        except Exception:
            pass
        return hashlib.sha256(raw.encode()).digest()
    return _EPHEMERAL_KEY


def is_key_configured() -> bool:
    """True, если ключ шифрования задан явно в окружении (не эфемерный)."""
    return bool(os.getenv(_ENV_KEY, "").strip())


def _hkdf(master: bytes, info: bytes, length: int = 32) -> bytes:
    # HKDF-Expand (RFC 5869) с солью = нулям (extract пропущен: master уже 32 B).
    prk = hmac.new(b"\x00" * 32, master, hashlib.sha256).digest()
    okm, t, counter = b"", b"", 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    out, counter = b"", 0
    while len(out) < length:
        block = hmac.new(
            enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256
        ).digest()
        out += block
        counter += 1
    return out[:length]


def encrypt(plaintext: str) -> str:
    """Шифрует строку; возвращает токен вида ``enc:v1:<base64>``."""
    if plaintext is None:
        raise ValueError("plaintext must not be None")
    master = _master_key()
    enc_key = _hkdf(master, b"enc")
    mac_key = _hkdf(master, b"mac")
    nonce = secrets.token_bytes(_NONCE_LEN)
    data = plaintext.encode("utf-8")
    ct = bytes(a ^ b for a, b in zip(data, _keystream(enc_key, nonce, len(data))))
    tag = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
    blob = base64.urlsafe_b64encode(nonce + ct + tag).decode("ascii")
    return _PREFIX + blob


def is_encrypted(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIX)


def decrypt(token: str) -> str:
    """Расшифровывает токен ``enc:v1:...``. Бросает ValueError при подделке."""
    if not is_encrypted(token):
        raise ValueError("not an encrypted token")
    master = _master_key()
    enc_key = _hkdf(master, b"enc")
    mac_key = _hkdf(master, b"mac")
    raw = base64.urlsafe_b64decode(token[len(_PREFIX):])
    nonce, ct, tag = raw[:_NONCE_LEN], raw[_NONCE_LEN:-_MAC_LEN], raw[-_MAC_LEN:]
    expected = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, tag):
        raise ValueError("MAC verification failed")
    data = bytes(a ^ b for a, b in zip(ct, _keystream(enc_key, nonce, len(ct))))
    return data.decode("utf-8")


def mask(value: str | None) -> str:
    """Маскирует секрет для логов/админки — не раскрывает содержимое."""
    return "••••" if value else ""
