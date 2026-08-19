"""Сервисный слой: бизнес-логика подачи и обработки показаний."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlmodel import Session, select

from app.models import (
    Meter,
    Organization,
    Reading,
    ReadingSource,
    ReadingStatus,
    Unit,
)


def current_period(today: Optional[date] = None) -> str:
    today = today or date.today()
    return f"{today.year:04d}-{today.month:02d}"


def last_reading(session: Session, meter_id: int) -> Optional[Reading]:
    """Последнее по времени показание счётчика."""
    return session.exec(
        select(Reading)
        .where(Reading.meter_id == meter_id)
        .order_by(Reading.reading_date.desc(), Reading.id.desc())
    ).first()


def reading_for_period(
    session: Session, meter_id: int, period: str
) -> Optional[Reading]:
    return session.exec(
        select(Reading)
        .where(Reading.meter_id == meter_id, Reading.period == period)
    ).first()


def is_window_open(org: Organization, today: Optional[date] = None) -> bool:
    """Открыто ли окно подачи показаний для организации.

    Окно может пересекать границу месяца (напр. с 25 по 5 число).
    """
    today = today or date.today()
    d = today.day
    a, b = org.reading_day_from, org.reading_day_to
    if a <= b:
        return a <= d <= b
    return d >= a or d <= b


class ReadingValidationError(Exception):
    pass


def validate_and_build(
    session: Session,
    meter: Meter,
    value: float,
    period: str,
    *,
    source: ReadingSource = ReadingSource.WEB,
    submitted_by_id: Optional[int] = None,
    note: Optional[str] = None,
) -> Reading:
    """Проверяет новое показание и формирует объект Reading (не сохраняет).

    Правила:
    - показание не может быть меньше предыдущего (счётчик не «откручивается»);
    - расход не должен превышать порог правдоподобия из типа счётчика (аномалия);
    - вычисляется расход за период.
    """
    mtype = meter.meter_type
    prev = last_reading(session, meter.id)
    prev_value = prev.value if prev else meter.initial_value

    if value < prev_value:
        raise ReadingValidationError(
            f"Rādījums ({value}) nevar būt mazāks par iepriekšējo ({prev_value})."
        )

    consumption = round(value - prev_value, mtype.decimals if mtype else 3)

    is_anomaly = False
    if mtype and consumption > mtype.max_plausible_consumption:
        is_anomaly = True
    if mtype and not mtype.allow_zero_consumption and consumption == 0:
        is_anomaly = True

    reading = Reading(
        meter_id=meter.id,
        period=period,
        value=value,
        consumption=consumption,
        reading_date=date.today(),
        source=source,
        status=ReadingStatus.SUBMITTED,
        is_anomaly=is_anomaly,
        submitted_by_id=submitted_by_id,
        note=note,
    )
    return reading


def upsert_reading(
    session: Session,
    meter: Meter,
    value: float,
    period: str,
    **kwargs,
) -> Reading:
    """Создаёт или обновляет показание за период (повторная подача заменяет)."""
    existing = reading_for_period(session, meter.id, period)
    new = validate_and_build(session, meter, value, period, **kwargs)
    if existing:
        existing.value = new.value
        existing.consumption = new.consumption
        existing.reading_date = new.reading_date
        existing.source = new.source
        existing.status = new.status
        existing.is_anomaly = new.is_anomaly
        existing.submitted_by_id = new.submitted_by_id
        existing.note = new.note
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    session.add(new)
    session.commit()
    session.refresh(new)
    return new


def meters_for_unit(session: Session, unit_id: int) -> list[Meter]:
    return list(
        session.exec(
            select(Meter).where(Meter.unit_id == unit_id, Meter.is_active == True)  # noqa: E712
        ).all()
    )


def readings_history(
    session: Session, meter_id: int, limit: int = 12
) -> list[Reading]:
    """Последние показания счётчика по возрастанию периода (для истории/графика)."""
    rows = session.exec(
        select(Reading)
        .where(Reading.meter_id == meter_id)
        .order_by(Reading.period.desc(), Reading.id.desc())
    ).all()
    rows = list(rows)[:limit]
    rows.reverse()  # по возрастанию: старые → новые
    return rows


def average_consumption(
    session: Session, meter_id: int, months: int = 12
) -> Optional[float]:
    """Среднемесячный расход за последние N месяцев (норма §41).

    Учитываются только реальные (не расчётные) показания с положительным
    расходом. Возвращает None, если истории недостаточно.
    """
    rows = session.exec(
        select(Reading)
        .where(
            Reading.meter_id == meter_id,
            Reading.source != ReadingSource.ESTIMATED,
        )
        .order_by(Reading.period.desc(), Reading.id.desc())
    ).all()
    values = [
        r.consumption for r in list(rows)[:months]
        if r.consumption is not None and r.consumption >= 0
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def estimate_reading(
    session: Session, meter: Meter, period: str,
) -> Optional[Reading]:
    """Формирует расчётное показание по §41 (среднее за 12 мес.), не сохраняя.

    Применяется, если житель не подал показание за период: к последнему
    показанию прибавляется среднемесячный расход. Возвращает None, если нет
    истории для оценки.
    """
    avg = average_consumption(session, meter.id)
    if avg is None:
        return None
    prev = last_reading(session, meter.id)
    prev_value = prev.value if prev else meter.initial_value
    mtype = meter.meter_type
    decimals = mtype.decimals if mtype else 3
    value = round(prev_value + avg, decimals)
    return Reading(
        meter_id=meter.id,
        period=period,
        value=value,
        consumption=round(avg, decimals),
        reading_date=date.today(),
        source=ReadingSource.ESTIMATED,
        status=ReadingStatus.SUBMITTED,
        is_anomaly=False,
        note="§41: aprēķināts pēc vidējā patēriņa (12 mēn.)",
    )


def units_for_user(session: Session, user_id: int) -> list[Unit]:
    from app.models import UnitResident

    links = session.exec(
        select(UnitResident).where(UnitResident.user_id == user_id)
    ).all()
    unit_ids = [l.unit_id for l in links]
    if not unit_ids:
        return []
    return list(session.exec(select(Unit).where(Unit.id.in_(unit_ids))).all())
