"""OPS-001 — аудит действий с показаниями.

Каждая mutating-операция с показаниями (подача/изменение) обязана оставить
неизменяемую запись в audit_log: кто, что, когда, старое/новое значение.
"""
from __future__ import annotations

from app.audit import record_audit
from app.models import AuditLog
from app.services import upsert_reading


def _audit_rows(session, entity_type: str):
    return (
        session.query(AuditLog)
        .filter(AuditLog.entity_type == entity_type)
        .all()
    )


def test_reading_change_writes_audit(session, factory):
    org, b, unit, mt, meter = factory.tenant_stack()
    resident = factory.resident_of(unit, organization=org)

    # Первая подача → создание.
    r1 = upsert_reading(
        session, meter, 110.0, "2026-08",
        submitted_by_id=resident.id, actor_id=resident.id,
    )
    rows = _audit_rows(session, "reading")
    assert len(rows) == 1
    assert rows[0].action == "reading_create"
    assert rows[0].actor_id == resident.id
    assert rows[0].entity_id == r1.id
    assert rows[0].new_value["value"] == 110.0

    # Повторная подача за тот же период → изменение (со старым/новым значением).
    upsert_reading(
        session, meter, 120.0, "2026-08",
        submitted_by_id=resident.id, actor_id=resident.id,
    )
    rows = _audit_rows(session, "reading")
    assert len(rows) == 2
    change = [r for r in rows if r.action == "reading_update"]
    assert len(change) == 1
    assert change[0].old_value["value"] == 110.0
    assert change[0].new_value["value"] == 120.0


def test_audit_log_is_append_only(session, factory):
    """record_audit только добавляет записи; повторные вызовы не мутируют старые."""
    record_audit(session, actor_id=1, action="reading_create",
                 entity_type="reading", entity_id=7,
                 old_value=None, new_value={"value": 5.0})
    record_audit(session, actor_id=1, action="reading_update",
                 entity_type="reading", entity_id=7,
                 old_value={"value": 5.0}, new_value={"value": 6.0})
    rows = _audit_rows(session, "reading")
    assert len(rows) == 2
    assert {r.action for r in rows} == {"reading_create", "reading_update"}
