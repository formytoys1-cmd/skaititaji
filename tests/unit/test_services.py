"""Юнит-тесты сервисного слоя (app/services.py): валидация, аномалии, окно,
история, среднее, §41-оценка, upsert."""
from datetime import date

import pytest

from app.models import ReadingSource
from app.services import (
    ReadingValidationError,
    average_consumption,
    current_period,
    estimate_reading,
    is_window_open,
    last_reading,
    reading_for_period,
    readings_history,
    upsert_reading,
    validate_and_build,
)

pytestmark = pytest.mark.unit


def test_current_period_format():
    assert current_period(date(2026, 3, 7)) == "2026-03"
    assert current_period(date(2026, 12, 31)) == "2026-12"


def test_window_open_same_month_range():
    class Org:
        reading_day_from = 10
        reading_day_to = 20
    assert is_window_open(Org(), date(2026, 5, 15)) is True
    assert is_window_open(Org(), date(2026, 5, 9)) is False
    assert is_window_open(Org(), date(2026, 5, 21)) is False


def test_window_open_crossing_month_boundary():
    class Org:
        reading_day_from = 25
        reading_day_to = 5
    assert is_window_open(Org(), date(2026, 5, 27)) is True   # >= 25
    assert is_window_open(Org(), date(2026, 5, 3)) is True    # <= 5
    assert is_window_open(Org(), date(2026, 5, 15)) is False


def test_validate_rejects_decreasing_reading(session, factory):
    org, b, u, mt, m = factory.tenant_stack()
    factory.reading(m, "2026-01", value=120.0)
    with pytest.raises(ReadingValidationError):
        validate_and_build(session, m, 100.0, "2026-02")  # ниже предыдущего


def test_validate_flags_anomaly_over_threshold(session, factory):
    org = factory.organization()
    b = factory.building(org)
    u = factory.unit(b)
    mt = factory.meter_type(max_plausible_consumption=10.0)
    m = factory.meter(u, mt, initial_value=0.0)
    r = validate_and_build(session, m, 500.0, "2026-02")
    assert r.is_anomaly is True
    assert r.consumption == 500.0


def test_upsert_creates_then_replaces(session, factory):
    org, b, u, mt, m = factory.tenant_stack()
    r1 = upsert_reading(session, m, 105.0, "2026-02")
    assert r1.value == 105.0
    # повторная подача за тот же период заменяет, а не дублирует
    r2 = upsert_reading(session, m, 108.0, "2026-02")
    assert r2.value == 108.0
    got = reading_for_period(session, m.id, "2026-02")
    assert got.value == 108.0


def test_last_reading_returns_latest(session, factory):
    org, b, u, mt, m = factory.tenant_stack()
    factory.reading(m, "2026-01", value=110.0,
                    reading_date=date(2026, 1, 20))
    factory.reading(m, "2026-02", value=115.0,
                    reading_date=date(2026, 2, 20))
    assert last_reading(session, m.id).value == 115.0


def test_history_and_average(session, factory):
    org, b, u, mt, m = factory.tenant_stack()
    for i, (period, val, cons) in enumerate([
        ("2026-01", 103.0, 3.0),
        ("2026-02", 106.5, 3.5),
        ("2026-03", 110.0, 3.5),
    ]):
        factory.reading(m, period, value=val, consumption=cons,
                        reading_date=date(2026, i + 1, 20))
    hist = readings_history(session, m.id, limit=12)
    assert [h.period for h in hist] == ["2026-01", "2026-02", "2026-03"]
    avg = average_consumption(session, m.id)
    assert avg == pytest.approx((3.0 + 3.5 + 3.5) / 3, rel=1e-3)


def test_estimate_reading_uses_average(session, factory):
    org, b, u, mt, m = factory.tenant_stack()
    factory.reading(m, "2026-01", value=104.0, consumption=4.0,
                    reading_date=date(2026, 1, 20))
    factory.reading(m, "2026-02", value=108.0, consumption=4.0,
                    reading_date=date(2026, 2, 20))
    est = estimate_reading(session, m, "2026-03")
    assert est is not None
    assert est.source == ReadingSource.ESTIMATED
    # прибавили среднее (4.0) к последнему показанию (108.0)
    assert est.value == pytest.approx(112.0, rel=1e-3)


def test_estimate_reading_none_without_history(session, factory):
    org, b, u, mt, m = factory.tenant_stack()
    assert estimate_reading(session, m, "2026-03") is None
