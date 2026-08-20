"""Фабрики синтетических данных для тестов.

СТРОГО: только выдуманные данные (без реальных персональных данных, лицевых
счетов и учёток). Каждый вызов создаёт валидную сущность в переданной сессии.
"""
from __future__ import annotations

import itertools
from datetime import date

from sqlmodel import Session

from app.auth import hash_password
from app.models import (
    Building,
    Meter,
    MeterCategory,
    MeterType,
    Organization,
    Reading,
    ReadingSource,
    ReadingStatus,
    Unit,
    UnitResident,
    User,
    UserRole,
)

_counter = itertools.count(1)


def _n() -> int:
    return next(_counter)


class Factory:
    """Набор фабрик, привязанных к конкретной сессии БД."""

    def __init__(self, session: Session) -> None:
        self.s = session

    # --- Организации / объекты ------------------------------------------- #
    def organization(self, **kw) -> Organization:
        i = _n()
        org = Organization(
            slug=kw.pop("slug", f"org-{i}"),
            name=kw.pop("name", f"Test Org {i}"),
            kind=kw.pop("kind", "manager"),
            **kw,
        )
        self.s.add(org)
        self.s.commit()
        self.s.refresh(org)
        return org

    def building(self, org: Organization, **kw) -> Building:
        b = Building(
            organization_id=org.id,
            address=kw.pop("address", f"Test iela {_n()}"),
            **kw,
        )
        self.s.add(b)
        self.s.commit()
        self.s.refresh(b)
        return b

    def unit(self, building: Building, **kw) -> Unit:
        i = _n()
        u = Unit(
            building_id=building.id,
            number=kw.pop("number", str(i)),
            account_number=kw.pop("account_number", f"ACC-{i}"),
            **kw,
        )
        self.s.add(u)
        self.s.commit()
        self.s.refresh(u)
        return u

    # --- Пользователи ----------------------------------------------------- #
    def user(
        self,
        *,
        organization: Organization | None = None,
        role: UserRole = UserRole.RESIDENT,
        password: str = "test-pass-123",
        email: str | None = None,
        **kw,
    ) -> User:
        i = _n()
        u = User(
            organization_id=(organization.id if organization else None),
            email=email or f"user{i}@test.local",
            full_name=kw.pop("full_name", f"Test User {i}"),
            password_hash=hash_password(password),
            role=role,
            **kw,
        )
        self.s.add(u)
        self.s.commit()
        self.s.refresh(u)
        return u

    def resident_of(self, unit: Unit, *, organization: Organization, **kw) -> User:
        u = self.user(organization=organization, role=UserRole.RESIDENT, **kw)
        self.s.add(UnitResident(user_id=u.id, unit_id=unit.id, relation="owner"))
        self.s.commit()
        return u

    # --- Счётчики / показания -------------------------------------------- #
    def meter_type(self, **kw) -> MeterType:
        i = _n()
        mt = MeterType(
            code=kw.pop("code", f"type_{i}"),
            category=kw.pop("category", MeterCategory.WATER),
            name_lv=kw.pop("name_lv", f"Tips {i}"),
            name_ru=kw.pop("name_ru", f"Тип {i}"),
            name_en=kw.pop("name_en", f"Type {i}"),
            **kw,
        )
        self.s.add(mt)
        self.s.commit()
        self.s.refresh(mt)
        return mt

    def meter(self, unit: Unit, meter_type: MeterType, **kw) -> Meter:
        i = _n()
        m = Meter(
            unit_id=unit.id,
            meter_type_id=meter_type.id,
            serial_number=kw.pop("serial_number", f"SN-{i}"),
            initial_value=kw.pop("initial_value", 0.0),
            **kw,
        )
        self.s.add(m)
        self.s.commit()
        self.s.refresh(m)
        return m

    def reading(self, meter: Meter, period: str, value: float, **kw) -> Reading:
        r = Reading(
            meter_id=meter.id,
            period=period,
            value=value,
            consumption=kw.pop("consumption", None),
            reading_date=kw.pop("reading_date", date.today()),
            source=kw.pop("source", ReadingSource.WEB),
            status=kw.pop("status", ReadingStatus.SUBMITTED),
            **kw,
        )
        self.s.add(r)
        self.s.commit()
        self.s.refresh(r)
        return r

    # --- Удобный композит: организация с домом/квартирой/счётчиком -------- #
    def tenant_stack(self):
        """Возвращает (org, building, unit, meter_type, meter) — готовый арендатор."""
        org = self.organization()
        b = self.building(org)
        u = self.unit(b)
        mt = self.meter_type()
        m = self.meter(u, mt, initial_value=100.0)
        return org, b, u, mt, m
