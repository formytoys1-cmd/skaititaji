"""window_status: даты открытия/закрытия окна подачи, в т.ч. через границу месяца."""
from datetime import date

import pytest

from app.models import Organization
from app.services import window_status

pytestmark = pytest.mark.unit


def _org(a, b):
    return Organization(slug="o", name="O", reading_day_from=a, reading_day_to=b)


def test_window_within_month_open():
    org = _org(10, 20)
    w = window_status(org, today=date(2026, 6, 15))
    assert w["open"] is True
    assert w["opens_on"] == date(2026, 6, 10)
    assert w["closes_on"] == date(2026, 6, 20)


def test_window_within_month_before_open():
    org = _org(10, 20)
    w = window_status(org, today=date(2026, 6, 5))
    assert w["open"] is False
    assert w["opens_on"] == date(2026, 6, 10)


def test_window_within_month_after_close_next_month():
    org = _org(10, 20)
    w = window_status(org, today=date(2026, 6, 25))
    assert w["open"] is False
    assert w["opens_on"] == date(2026, 7, 10)


def test_window_cross_month_open_late():
    # окно 25 → 5: сегодня 27-е → открыто, закроется 5 числа след. месяца
    org = _org(25, 5)
    w = window_status(org, today=date(2026, 6, 27))
    assert w["open"] is True
    assert w["opens_on"] == date(2026, 6, 25)
    assert w["closes_on"] == date(2026, 7, 5)


def test_window_cross_month_open_early():
    # окно 25 → 5: сегодня 3-е → открыто (с 25 прошлого месяца), закроется 5-го
    org = _org(25, 5)
    w = window_status(org, today=date(2026, 6, 3))
    assert w["open"] is True
    assert w["opens_on"] == date(2026, 5, 25)
    assert w["closes_on"] == date(2026, 6, 5)


def test_window_cross_month_closed():
    # окно 25 → 5: сегодня 15-е → закрыто, откроется 25-го этого месяца
    org = _org(25, 5)
    w = window_status(org, today=date(2026, 6, 15))
    assert w["open"] is False
    assert w["opens_on"] == date(2026, 6, 25)
    assert w["closes_on"] == date(2026, 7, 5)


def test_window_year_boundary():
    org = _org(25, 5)
    w = window_status(org, today=date(2026, 12, 28))
    assert w["open"] is True
    assert w["closes_on"] == date(2027, 1, 5)
