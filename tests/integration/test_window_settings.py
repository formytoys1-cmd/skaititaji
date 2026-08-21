"""Интеграция: настройка окна подачи управляющим + отражение в UI."""
import re

import pytest
from sqlmodel import Session, select

from app.models import Organization

pytestmark = pytest.mark.integration


def _csrf(client):
    html = client.get("/login").text
    return re.search(r'name="csrf_token"\s+value="([^"]+)"', html).group(1)


def _login(client, email, csrf):
    return client.post("/login", data={"email": email, "password": "demo1234",
                                       "csrf_token": csrf}, follow_redirects=False)


def test_manager_can_open_settings(client, csrf):
    _login(client, "manager@demo.lv", csrf)
    r = client.get("/parvalde/iestatijumi")
    assert r.status_code == 200
    assert "reading_day_from" in r.text


def test_manager_saves_window(client, engine, csrf):
    _login(client, "manager@demo.lv", csrf)
    r = client.post("/parvalde/iestatijumi",
                    data={"reading_day_from": "10", "reading_day_to": "20",
                          "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        org = s.exec(select(Organization)).first()
        assert org.reading_day_from == 10
        assert org.reading_day_to == 20


def test_window_days_clamped(client, engine, csrf):
    _login(client, "manager@demo.lv", csrf)
    client.post("/parvalde/iestatijumi",
                data={"reading_day_from": "0", "reading_day_to": "99",
                      "csrf_token": csrf}, follow_redirects=False)
    with Session(engine) as s:
        org = s.exec(select(Organization)).first()
        assert org.reading_day_from == 1     # clamp 1..28
        assert org.reading_day_to == 28


def test_resident_sees_window_dates(client, csrf):
    # житель видит баннер окна с датой (демо-резидент)
    _login(client, "resident@demo.lv", csrf)
    r = client.get("/dzivoklis")
    assert r.status_code == 200
    # присутствует блок периода
    assert "Nodošanas periods" in r.text or "Период подачи" in r.text \
        or "Submission window" in r.text
