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


def _clamp_day(year: int, month: int, day: int) -> date:
    """Возвращает дату с днём day, но не больше последнего дня месяца."""
    import calendar
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _add_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _sub_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def window_status(org: Organization, today: Optional[date] = None) -> dict:
    """Статус окна подачи с конкретными датами.

    Возвращает dict:
      - open: bool — открыто ли окно сейчас;
      - day_from, day_to: int — настроенные дни месяца;
      - opens_on: date — дата ближайшего открытия (если закрыто) или текущего
        открытия (если открыто);
      - closes_on: date — дата ближайшего закрытия (последний день приёма).
    Корректно обрабатывает окно, пересекающее границу месяца (напр. 25→5).
    """
    today = today or date.today()
    a, b = org.reading_day_from, org.reading_day_to
    y, m, d = today.year, today.month, today.day
    is_open = is_window_open(org, today)

    if a <= b:
        # Окно внутри одного месяца: [a..b].
        if is_open:
            opens_on = _clamp_day(y, m, a)
            closes_on = _clamp_day(y, m, b)
        elif d < a:
            opens_on = _clamp_day(y, m, a)
            closes_on = _clamp_day(y, m, b)
        else:  # d > b — следующее окно в следующем месяце
            ny, nm = _add_month(y, m)
            opens_on = _clamp_day(ny, nm, a)
            closes_on = _clamp_day(ny, nm, b)
    else:
        # Окно через границу месяца: [a..конец] ∪ [начало..b].
        if is_open:
            if d >= a:
                # открылось в этом месяце, закроется b числом след. месяца
                opens_on = _clamp_day(y, m, a)
                ny, nm = _add_month(y, m)
                closes_on = _clamp_day(ny, nm, b)
            else:
                # открылось a числом прошлого месяца, закроется b в этом
                py, pm = _sub_month(y, m)
                opens_on = _clamp_day(py, pm, a)
                closes_on = _clamp_day(y, m, b)
        else:
            # закрыто: b < d < a → ближайшее открытие a числом этого месяца
            opens_on = _clamp_day(y, m, a)
            ny, nm = _add_month(y, m)
            closes_on = _clamp_day(ny, nm, b)

    return {
        "open": is_open,
        "day_from": a,
        "day_to": b,
        "opens_on": opens_on,
        "closes_on": closes_on,
    }


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
    *,
    actor_id: Optional[int] = None,
    **kwargs,
) -> Reading:
    """Создаёт или обновляет показание за период (идемпотентно, без гонок).

    DATA-002:
    - уникальность (meter_id, period) гарантируется БД-констрейнтом;
    - при гонке (две параллельные вставки) одна из них получит IntegrityError —
      мы откатываемся и повторяем как обновление уже существующей строки;
    - правило «новое показание ≥ предыдущего» проверяется в validate_and_build.

    OPS-001: любая mutating-операция пишет неизменяемую запись в audit_log
    (создание — ``reading_create``, обновление — ``reading_update``). ``actor_id``
    — кто выполняет действие (может отличаться от submitted_by_id).
    """
    from sqlalchemy.exc import IntegrityError, OperationalError

    from app.audit import record_audit

    def _snapshot(r: Reading) -> dict:
        return {
            "value": r.value,
            "consumption": r.consumption,
            "period": r.period,
            "status": r.status.value,
            "source": r.source.value,
        }

    def _audit(action: str, reading: Reading, old: Optional[dict]) -> None:
        record_audit(
            session,
            actor_id=actor_id,
            action=action,
            entity_type="reading",
            entity_id=reading.id,
            old_value=old,
            new_value=_snapshot(reading),
            commit=False,
        )
        session.commit()

    def _apply(existing: Reading, new: Reading) -> None:
        existing.value = new.value
        existing.consumption = new.consumption
        existing.reading_date = new.reading_date
        existing.source = new.source
        existing.status = new.status
        existing.is_anomaly = new.is_anomaly
        existing.submitted_by_id = new.submitted_by_id
        existing.note = new.note

    existing = reading_for_period(session, meter.id, period)
    new = validate_and_build(session, meter, value, period, **kwargs)
    if existing:
        old_snapshot = _snapshot(existing)
        _apply(existing, new)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        _audit("reading_update", existing, old_snapshot)
        return existing

    session.add(new)
    try:
        session.commit()
    except (IntegrityError, OperationalError):
        # Гонка: параллельная транзакция уже вставила/заблокировала строку за
        # этот период. Откатываемся и применяем как обновление существующей.
        session.rollback()
        existing = reading_for_period(session, meter.id, period)
        if existing is None:
            # Строки нет (напр. таймаут блокировки без вставки) — повторяем вставку.
            retry = validate_and_build(session, meter, value, period, **kwargs)
            session.add(retry)
            session.commit()
            session.refresh(retry)
            _audit("reading_create", retry, None)
            return retry
        old_snapshot = _snapshot(existing)
        rebuilt = validate_and_build(session, meter, value, period, **kwargs)
        _apply(existing, rebuilt)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        _audit("reading_update", existing, old_snapshot)
        return existing
    session.refresh(new)
    _audit("reading_create", new, None)
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
