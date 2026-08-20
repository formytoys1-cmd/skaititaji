"""DATA-002: идемпотентность и защита от гонок при подаче показаний.

Проверяем, что за один (meter_id, period) не может появиться дубликат,
что показание не может убывать, и что параллельная подача не создаёт двух строк.
"""
from __future__ import annotations

import threading

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Reading
from app.services import ReadingValidationError, upsert_reading

pytestmark = pytest.mark.unit


def test_reading_idempotent_same_period(session, factory):
    """Повторная подача за тот же период не плодит строки (upsert)."""
    org, b, u, mt, m = factory.tenant_stack()
    upsert_reading(session, m, 105.0, "2026-02")
    upsert_reading(session, m, 110.0, "2026-02")

    rows = session.exec(
        select(Reading).where(Reading.meter_id == m.id, Reading.period == "2026-02")
    ).all()
    assert len(rows) == 1
    assert rows[0].value == 110.0


def test_reading_not_decreasing(session, factory):
    """Новое показание за период не может быть меньше предыдущего."""
    org, b, u, mt, m = factory.tenant_stack()
    factory.reading(m, "2026-01", value=120.0)
    with pytest.raises(ReadingValidationError):
        upsert_reading(session, m, 100.0, "2026-02")


def test_concurrent_submit_no_duplicate(tmp_path, factory):
    """Параллельная подача за один (meter_id, period) не создаёт дубликат.

    Используем файловую SQLite (у каждого потока — своё реальное соединение),
    чтобы смоделировать настоящую гонку двух транзакций. БД-уникальность
    (meter_id, period) должна оставить ровно одну строку.
    """
    db_url = f"sqlite:///{tmp_path / 'concurrent.db'}"
    engine = create_engine(
        db_url, connect_args={"check_same_thread": False, "timeout": 30}
    )
    SQLModel.metadata.create_all(engine)

    from tests.factories import Factory

    with Session(engine) as s:
        f = Factory(s)
        org, b, u, mt, m = f.tenant_stack()
        meter_id = m.id
        meter_cls = type(m)

    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def submit(value: float) -> None:
        try:
            with Session(engine) as s:
                mm = s.get(meter_cls, meter_id)
                barrier.wait()
                upsert_reading(s, mm, value, "2026-03")
        except Exception as exc:  # noqa: BLE001 — фиксируем для проверки
            errors.append(exc)

    t1 = threading.Thread(target=submit, args=(150.0,))
    t2 = threading.Thread(target=submit, args=(160.0,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    with Session(engine) as s:
        rows = s.exec(
            select(Reading).where(
                Reading.meter_id == meter_id, Reading.period == "2026-03"
            )
        ).all()

    engine.dispose()
    assert len(rows) == 1, f"ожидалась одна строка, получено {len(rows)}"
