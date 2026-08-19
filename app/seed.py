"""Каталог типов счётчиков по умолчанию и генерация демо-данных."""
from __future__ import annotations

from datetime import date, timedelta

from sqlmodel import Session, select

from app.auth import hash_password
from app.database import engine, init_db
from app.models import (
    Building,
    IntegrationLog,  # noqa: F401  (регистрация модели)
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

# --------------------------------------------------------------------------- #
# Каталог типов счётчиков (config-driven). Добавить тип = добавить запись.
# --------------------------------------------------------------------------- #
DEFAULT_METER_TYPES = [
    dict(code="cold_water", category=MeterCategory.WATER,
         name_lv="Aukstais ūdens", name_ru="Холодная вода", name_en="Cold water",
         unit="m³", decimals=3, icon="💧", color="#0ea5e9", sort_order=10,
         max_plausible_consumption=60.0),
    dict(code="hot_water", category=MeterCategory.WATER,
         name_lv="Karstais ūdens", name_ru="Горячая вода", name_en="Hot water",
         unit="m³", decimals=3, icon="🔥", color="#ef4444", sort_order=20,
         max_plausible_consumption=40.0),
    dict(code="electricity", category=MeterCategory.ENERGY,
         name_lv="Elektroenerģija", name_ru="Электроэнергия", name_en="Electricity",
         unit="kWh", decimals=1, icon="⚡", color="#f59e0b", sort_order=30,
         max_plausible_consumption=2000.0),
    dict(code="gas", category=MeterCategory.GAS,
         name_lv="Gāze", name_ru="Газ", name_en="Gas",
         unit="m³", decimals=2, icon="🟦", color="#3b82f6", sort_order=40,
         max_plausible_consumption=500.0),
    dict(code="heat", category=MeterCategory.HEAT,
         name_lv="Siltumenerģija", name_ru="Тепло", name_en="Heat",
         unit="MWh", decimals=3, icon="♨️", color="#f97316", sort_order=50,
         max_plausible_consumption=10.0),
]


def ensure_meter_types(session: Session) -> dict[str, MeterType]:
    existing = {mt.code: mt for mt in session.exec(select(MeterType)).all()}
    for spec in DEFAULT_METER_TYPES:
        if spec["code"] not in existing:
            mt = MeterType(**spec)
            session.add(mt)
            existing[spec["code"]] = mt
    session.commit()
    return {mt.code: mt for mt in session.exec(select(MeterType)).all()}


def _period(offset_months: int) -> str:
    d = date.today().replace(day=1)
    for _ in range(offset_months):
        d = (d - timedelta(days=1)).replace(day=1)
    return f"{d.year:04d}-{d.month:02d}"


def seed_demo(reset: bool = False) -> None:
    init_db()
    with Session(engine) as session:
        types = ensure_meter_types(session)

        # Идемпотентность: если демо-организация уже есть — не дублируем
        org = session.exec(
            select(Organization).where(Organization.slug == "demo-nams")
        ).first()
        if org and not reset:
            return

        # --- Организация (управляющий) ------------------------------------ #
        org = Organization(
            slug="demo-nams",
            name="Demo Namu Pārvalde",
            legal_name='SIA "Demo Namu Pārvalde"',
            reg_number="40000000000",
            kind="manager",
            email="info@demonams.lv",
            phone="+371 20000000",
            address="Brīvības iela 1, Rīga",
            brand_color="#0ea5e9",
            logo_text="Demo Nams",
            reading_day_from=25,
            reading_day_to=5,
            integration_provider="visma_horizon",
            integration_config={"mock": True},
        )
        session.add(org)
        session.commit()
        session.refresh(org)

        # --- Дом ---------------------------------------------------------- #
        building = Building(
            organization_id=org.id,
            name="Māja Nr. 1",
            address="Brīvības iela 1, Rīga, LV-1010",
            external_id="HZ-OBJ-1",
        )
        session.add(building)
        session.commit()
        session.refresh(building)

        # --- Квартиры + счётчики + жители --------------------------------- #
        residents_data = [
            ("12", "resident@demo.lv", "Jānis Bērziņš", [123.456, 87.201]),
            ("15", "anna@demo.lv", "Anna Kalniņa", [201.100, 142.500]),
            ("23", "peteris@demo.lv", "Pēteris Ozols", [55.900, 33.100]),
        ]
        first_unit = None
        for num, email, name, (cold0, hot0) in residents_data:
            unit = Unit(
                building_id=building.id,
                number=num,
                account_number=f"LV-{building.id}-{num}",
                area_m2=52.0,
                residents_count=2,
                external_id=f"HZ-UNIT-{num}",
            )
            session.add(unit)
            session.commit()
            session.refresh(unit)
            if first_unit is None:
                first_unit = unit

            cold = Meter(unit_id=unit.id, meter_type_id=types["cold_water"].id,
                         serial_number=f"AK-{num}-CW", location="Vannas istaba",
                         initial_value=cold0 - 5, external_id=f"HZ-M-{num}-CW",
                         verification_due=date.today() + timedelta(days=400))
            hot = Meter(unit_id=unit.id, meter_type_id=types["hot_water"].id,
                        serial_number=f"AK-{num}-HW", location="Vannas istaba",
                        initial_value=hot0 - 3, external_id=f"HZ-M-{num}-HW",
                        verification_due=date.today() + timedelta(days=400))
            session.add(cold)
            session.add(hot)
            session.commit()
            session.refresh(cold)
            session.refresh(hot)

            # История показаний за 3 прошедших периода
            for i, meter in ((0, cold), (1, hot)):
                base = (cold0 - 5) if i == 0 else (hot0 - 3)
                val = base
                for m in range(3, 0, -1):
                    val = round(val + (3.2 if i == 0 else 1.8), 3)
                    session.add(Reading(
                        meter_id=meter.id, period=_period(m), value=val,
                        consumption=(3.2 if i == 0 else 1.8),
                        reading_date=date.today() - timedelta(days=30 * m),
                        source=ReadingSource.WEB, status=ReadingStatus.SYNCED,
                    ))
            session.commit()

            resident = User(
                organization_id=org.id, email=email, full_name=name,
                password_hash=hash_password("demo1234"),
                role=UserRole.RESIDENT, locale="lv",
            )
            session.add(resident)
            session.commit()
            session.refresh(resident)
            session.add(UnitResident(user_id=resident.id, unit_id=unit.id,
                                     relation="owner"))
            session.commit()

        # --- Управляющий и суперадмин ------------------------------------- #
        session.add(User(
            organization_id=org.id, email="manager@demo.lv",
            full_name="Māris Vadītājs",
            password_hash=hash_password("demo1234"),
            role=UserRole.MANAGER, locale="lv",
        ))
        session.add(User(
            organization_id=None, email="admin@demo.lv",
            full_name="Platform Admin",
            password_hash=hash_password("demo1234"),
            role=UserRole.SUPERADMIN, locale="lv",
        ))
        session.commit()


if __name__ == "__main__":
    import sys

    seed_demo(reset="--reset" in sys.argv)
    print("Demo dati sagatavoti. Ieeja: manager@demo.lv / resident@demo.lv (parole: demo1234)")
