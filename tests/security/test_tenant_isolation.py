"""SEC-008 — Изоляция арендаторов (multi-tenant): защита от IDOR.

Reproduce → Fix → Verify → Guard.

Мультиарендность построена на модели Organization; каждый доступ к сущности
по прямому id из URL/формы обязан проверять принадлежность организации
текущего пользователя. Здесь мы создаём ДВУХ арендаторов (A и B) и проверяем,
что пользователь арендатора A НЕ может читать/менять данные арендатора B по
прямому id (классический IDOR): ожидаем «не найдено» (редирект/403/404), а не
успешный доступ к чужим данным.
"""
from __future__ import annotations

import pytest

from app.models import UserRole
from tests.conftest import csrf_token
from tests.factories import Factory

pytestmark = pytest.mark.security

_PASSWORD = "tenant-pass-123"


def _login(client, email: str) -> None:
    """Логинит пользователя через боевой POST /login (сессионная cookie)."""
    r = client.post(
        "/login",
        data={"email": email, "password": _PASSWORD, "csrf_token": csrf_token(client)},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), r.text
    # Успешный логин НЕ ведёт обратно на /login.
    assert r.headers.get("location") != "/login", "аутентификация не удалась"


@pytest.fixture()
def two_tenants(session):
    """Два независимых арендатора A и B со своей структурой и менеджером/жителем."""
    f = Factory(session)

    def _mk(prefix: str):
        org = f.organization(name=f"{prefix} Org")
        building = f.building(org)
        unit = f.unit(building)
        mt = f.meter_type()
        meter = f.meter(unit, mt, initial_value=100.0)
        reading = f.reading(meter, "2026-07", 150.0)
        manager = f.user(
            organization=org, role=UserRole.MANAGER,
            email=f"{prefix.lower()}-mgr@test.local", password=_PASSWORD,
        )
        resident = f.resident_of(
            unit, organization=org,
            email=f"{prefix.lower()}-res@test.local", password=_PASSWORD,
        )
        return {
            "org": org, "building": building, "unit": unit,
            "meter_type": mt, "meter": meter, "reading": reading,
            "manager": manager, "resident": resident,
        }

    return {"A": _mk("A"), "B": _mk("B")}


# --------------------------------------------------------------------------- #
# Менеджер арендатора A против объектов арендатора B (management.py)
# --------------------------------------------------------------------------- #
def test_manager_cannot_view_foreign_building(client, two_tenants):
    a, b = two_tenants["A"], two_tenants["B"]
    _login(client, a["manager"].email)

    r = client.get(f"/parvalde/objekti/{b['building'].id}", follow_redirects=False)
    # Чужой дом не должен раскрываться: либо 404, либо редирект «не найдено».
    assert r.status_code in (303, 404)
    if r.status_code == 303:
        assert r.headers["location"] == "/parvalde/objekti"


def test_manager_cannot_view_foreign_unit(client, two_tenants):
    a, b = two_tenants["A"], two_tenants["B"]
    _login(client, a["manager"].email)

    r = client.get(f"/parvalde/dzivoklis/{b['unit'].id}", follow_redirects=False)
    assert r.status_code in (303, 404)
    if r.status_code == 303:
        assert r.headers["location"] == "/parvalde/objekti"


def test_manager_cannot_create_unit_in_foreign_building(client, session, two_tenants):
    from sqlmodel import func, select

    from app.models import Unit

    a, b = two_tenants["A"], two_tenants["B"]
    _login(client, a["manager"].email)

    before = session.exec(
        select(func.count(Unit.id)).where(Unit.building_id == b["building"].id)
    ).one()
    r = client.post(
        f"/parvalde/objekti/{b['building'].id}/units",
        data={"number": "666", "account_number": "HACK",
              "csrf_token": csrf_token(client)},
        follow_redirects=False,
    )
    assert r.status_code in (303, 404)
    session.expire_all()
    after = session.exec(
        select(func.count(Unit.id)).where(Unit.building_id == b["building"].id)
    ).one()
    assert after == before, "менеджер A создал квартиру в доме арендатора B (IDOR)"


def test_manager_cannot_create_meter_in_foreign_unit(client, session, two_tenants):
    from sqlmodel import func, select

    from app.models import Meter

    a, b = two_tenants["A"], two_tenants["B"]
    _login(client, a["manager"].email)

    before = session.exec(
        select(func.count(Meter.id)).where(Meter.unit_id == b["unit"].id)
    ).one()
    r = client.post(
        f"/parvalde/dzivoklis/{b['unit'].id}/meters",
        data={
            "meter_type_id": b["meter_type"].id,
            "serial_number": "HACK-SN",
            "initial_value": "0",
            "csrf_token": csrf_token(client),
        },
        follow_redirects=False,
    )
    assert r.status_code in (303, 404)
    session.expire_all()
    after = session.exec(
        select(func.count(Meter.id)).where(Meter.unit_id == b["unit"].id)
    ).one()
    assert after == before, "менеджер A создал счётчик в квартире арендатора B (IDOR)"


# --------------------------------------------------------------------------- #
# Житель арендатора A против счётчиков арендатора B (resident.py)
# --------------------------------------------------------------------------- #
def test_resident_cannot_submit_reading_for_foreign_meter(client, session, two_tenants):
    from sqlmodel import func, select

    from app.models import Reading

    a, b = two_tenants["A"], two_tenants["B"]
    _login(client, a["resident"].email)

    period_meter = b["meter"]
    before = session.exec(
        select(func.count(Reading.id)).where(Reading.meter_id == period_meter.id)
    ).one()
    r = client.post(
        "/dzivoklis/submit",
        data={f"value_{period_meter.id}": "999",
              "csrf_token": csrf_token(client)},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    session.expire_all()
    after = session.exec(
        select(func.count(Reading.id)).where(Reading.meter_id == period_meter.id)
    ).one()
    assert after == before, "житель A подал показание на счётчик арендатора B (IDOR)"


# --------------------------------------------------------------------------- #
# Прямые unit-тесты аудируемого хелпера принадлежности (app/tenancy.py)
# --------------------------------------------------------------------------- #
def test_tenancy_helpers_reject_foreign_entities(session, two_tenants):
    from app.tenancy import owned_building, owned_meter, owned_unit

    a, b = two_tenants["A"], two_tenants["B"]
    org_a = a["org"]

    # Свои сущности — возвращаются.
    assert owned_building(session, org_a, a["building"].id) is not None
    assert owned_unit(session, org_a, a["unit"].id) is not None
    assert owned_meter(session, org_a, a["meter"].id) is not None

    # Чужие сущности арендатора B — отклоняются (None).
    assert owned_building(session, org_a, b["building"].id) is None
    assert owned_unit(session, org_a, b["unit"].id) is None
    assert owned_meter(session, org_a, b["meter"].id) is None

    # Несуществующие id — тоже None (без утечки исключений).
    assert owned_building(session, org_a, 10_000_001) is None
    assert owned_unit(session, org_a, 10_000_001) is None
    assert owned_meter(session, org_a, 10_000_001) is None
