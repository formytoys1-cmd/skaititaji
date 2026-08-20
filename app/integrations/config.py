"""Хранение и чтение секретов интеграций с шифрованием at-rest (SEC-003).

Секреты (пароль/токен Horizon) НЕ хранятся открытым текстом в
Organization.integration_config. Вместо ключа ``<name>`` в конфиг пишется
``<name>_enc`` с зашифрованным значением (см. app/secrets_crypto).

Совместимость: если в конфиге ещё лежит открытый ``<name>`` (наследие/сид),
чтение прозрачно его возвращает — это упрощает миграцию без падений.
"""
from __future__ import annotations

from typing import Optional

from app.models import Organization
from app.secrets_crypto import decrypt, encrypt, is_encrypted

_ENC_SUFFIX = "_enc"


def set_integration_secret(org: Organization, name: str, value: str) -> None:
    """Записывает секрет в зашифрованном виде, удаляя возможный открытый ключ."""
    cfg = dict(org.integration_config or {})
    cfg.pop(name, None)  # никогда не храним открытый текст
    cfg[name + _ENC_SUFFIX] = encrypt(value)
    org.integration_config = cfg  # реассайн для трекинга JSON-колонки


def get_integration_secret(org: Organization, name: str) -> Optional[str]:
    """Возвращает расшифрованный секрет (или открытый, если он ещё не мигрирован)."""
    cfg = org.integration_config or {}
    enc = cfg.get(name + _ENC_SUFFIX)
    if is_encrypted(enc):
        try:
            return decrypt(enc)
        except Exception:
            return None
    plain = cfg.get(name)
    return plain if plain else None


def has_integration_secret(org: Organization, name: str) -> bool:
    cfg = org.integration_config or {}
    return bool(cfg.get(name + _ENC_SUFFIX) or cfg.get(name))
