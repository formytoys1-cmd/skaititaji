"""OPS-001 — запись событий в неизменяемый журнал аудита.

`record_audit` — единственная точка создания записей `AuditLog`. Записи
append-only: приложение никогда не обновляет и не удаляет их.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session

from app.models import AuditLog


def _jsonable(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return {"value": value}


def record_audit(
    session: Session,
    *,
    actor_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int],
    old_value: Any = None,
    new_value: Any = None,
    commit: bool = True,
) -> AuditLog:
    """Создаёт запись аудита. По умолчанию коммитит (запись неизменяема)."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=_jsonable(old_value),
        new_value=_jsonable(new_value),
    )
    session.add(entry)
    if commit:
        session.commit()
        session.refresh(entry)
    return entry
