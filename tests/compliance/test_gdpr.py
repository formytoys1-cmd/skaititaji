"""GDPR-001 — процедуры экспорта и удаления персональных данных субъекта.

Данные жителя (User), его связей с квартирами (UnitResident) и показаний,
которые он подал (Reading.submitted_by_id), должны:
- экспортироваться в структурированном виде (право на переносимость, ст. 20 GDPR);
- удаляться/анонимизироваться по запросу субъекта с каскадом (ст. 17 GDPR),
  при этом обезличенные показания сохраняются для расчётов (законный интерес).

Все данные синтетические.
"""
from __future__ import annotations

from app.gdpr import (
    GdprAccessError,
    authorize_subject_access,
    erase_subject,
    export_subject_data,
)
from app.models import Reading, UnitResident, User, UserRole


def test_gdpr_export_subject_data(session, factory):
    org = factory.organization()
    b = factory.building(org)
    unit = factory.unit(b)
    mt = factory.meter_type()
    meter = factory.meter(unit, mt, initial_value=100.0)
    resident = factory.resident_of(unit, organization=org, full_name="Jānis Bērziņš")
    factory.reading(meter, "2026-07", 110.0, submitted_by_id=resident.id)
    factory.reading(meter, "2026-08", 120.0, submitted_by_id=resident.id)

    data = export_subject_data(session, resident.id)

    assert data["subject"]["id"] == resident.id
    assert data["subject"]["email"] == resident.email
    assert data["subject"]["full_name"] == "Jānis Bērziņš"
    # Все квартиры субъекта
    assert len(data["units"]) == 1
    assert data["units"][0]["unit_id"] == unit.id
    # Все показания, поданные субъектом
    assert {r["period"] for r in data["readings"]} == {"2026-07", "2026-08"}


def test_gdpr_erasure_cascades(session, factory):
    org = factory.organization()
    b = factory.building(org)
    unit = factory.unit(b)
    mt = factory.meter_type()
    meter = factory.meter(unit, mt, initial_value=100.0)
    resident = factory.resident_of(unit, organization=org, full_name="Anna Kalniņa")
    reading = factory.reading(meter, "2026-08", 120.0, submitted_by_id=resident.id)
    resident_id = resident.id
    reading_id = reading.id

    erase_subject(session, resident_id)

    # Учётка субъекта удалена
    assert session.get(User, resident_id) is None
    # Связи с квартирами удалены каскадом
    assert (
        session.query(UnitResident)
        .filter(UnitResident.user_id == resident_id)
        .count()
        == 0
    )
    # Показания сохранены, но обезличены (submitted_by_id обнулён)
    r = session.get(Reading, reading_id)
    assert r is not None
    assert r.value == 120.0
    assert r.submitted_by_id is None


def test_gdpr_access_denied_cross_tenant():
    """Управляющий одного арендатора не может выгрузить субъекта другого."""
    import pytest

    org_a = User(email="a", full_name="A", password_hash="x",
                 role=UserRole.MANAGER, organization_id=1)
    other_subject = User(email="b", full_name="B", password_hash="x",
                         role=UserRole.RESIDENT, organization_id=2)
    org_a.id = 10
    other_subject.id = 20
    with pytest.raises(GdprAccessError):
        authorize_subject_access(org_a, other_subject)


def test_gdpr_subject_accesses_own_data():
    from app.models import UserRole as _R
    subject = User(email="s", full_name="S", password_hash="x", role=_R.RESIDENT)
    subject.id = 5
    authorize_subject_access(subject, subject)  # не бросает
