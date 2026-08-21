"""Интеграция: массовая генерация квартир управляющим (apsaimniekotājs)."""
import re

import pytest
from sqlmodel import Session, func, select

from app.models import Unit

pytestmark = pytest.mark.integration


def _login_manager(client, csrf):
    r = client.post(
        "/login",
        data={"email": "manager@demo.lv", "password": "demo1234",
              "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/parvalde"


def _create_building(client, csrf) -> int:
    r = client.post(
        "/parvalde/objekti",
        data={"address": "Islices iela 3", "name": "Islices 3",
              "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303
    m = re.search(r"/parvalde/objekti/(\d+)", r.headers["location"])
    assert m
    return int(m.group(1))


def test_generate_119_series(client, engine, csrf):
    _login_manager(client, csrf)
    bid = _create_building(client, csrf)

    # 119 серия: 2 подъезда × 10 этажей × 4 кв = 80 квартир
    r = client.post(
        f"/parvalde/objekti/{bid}/generate",
        data={"entrances": "2", "floors": "10", "per_floor": "4",
              "start_number": "1", "max_residents": "2",
              "account_prefix": "", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303

    with Session(engine) as s:
        count = s.exec(
            select(func.count(Unit.id)).where(Unit.building_id == bid)
        ).one()
        assert count == 80
        sample = s.exec(select(Unit).where(Unit.building_id == bid)).first()
        assert sample.max_residents == 2
        assert sample.account_number  # присвоен лицевой счёт для регистрации


def test_generate_skips_existing_numbers(client, engine, csrf):
    _login_manager(client, csrf)
    bid = _create_building(client, csrf)

    data = {"entrances": "1", "floors": "2", "per_floor": "2",
            "start_number": "1", "max_residents": "2",
            "account_prefix": "", "csrf_token": csrf}
    client.post(f"/parvalde/objekti/{bid}/generate", data=data,
                follow_redirects=False)
    # повторная генерация тем же диапазоном — дублей не будет
    client.post(f"/parvalde/objekti/{bid}/generate", data=data,
                follow_redirects=False)

    with Session(engine) as s:
        count = s.exec(
            select(func.count(Unit.id)).where(Unit.building_id == bid)
        ).one()
        assert count == 4


def test_generate_rejects_absurd_total(client, engine, csrf):
    _login_manager(client, csrf)
    bid = _create_building(client, csrf)
    r = client.post(
        f"/parvalde/objekti/{bid}/generate",
        data={"entrances": "50", "floors": "50", "per_floor": "50",
              "start_number": "1", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 303
    with Session(engine) as s:
        count = s.exec(
            select(func.count(Unit.id)).where(Unit.building_id == bid)
        ).one()
        assert count == 0
