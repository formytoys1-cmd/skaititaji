"""Кабинет жителя: просмотр квартир, счётчиков и подача показаний."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.auth import require_user
from app.database import get_session
from app.models import Meter, Organization, User, UserRole
from app.services import (
    ReadingValidationError,
    current_period,
    is_window_open,
    last_reading,
    meters_for_unit,
    reading_for_period,
    units_for_user,
    upsert_reading,
)
from app.web import flash, render

router = APIRouter()


def _resident_org(session: Session, user: User) -> Organization | None:
    if user.organization_id:
        return session.get(Organization, user.organization_id)
    return None


@router.get("/dzivoklis")
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if user.role != UserRole.RESIDENT:
        return RedirectResponse("/", 303)

    org = _resident_org(session, user)
    units = units_for_user(session, user.id)
    period = current_period()
    window_open = is_window_open(org) if org else True

    unit_cards = []
    for unit in units:
        meters = meters_for_unit(session, unit.id)
        meter_rows = []
        for m in meters:
            prev = last_reading(session, m.id)
            this_period = reading_for_period(session, m.id, period)
            meter_rows.append({
                "meter": m,
                "type": m.meter_type,
                "prev": prev,
                "prev_value": prev.value if prev else m.initial_value,
                "current": this_period,
            })
        unit_cards.append({"unit": unit, "meters": meter_rows})

    return render(
        request, "resident/dashboard.html",
        {
            "unit_cards": unit_cards,
            "period": period,
            "window_open": window_open,
        },
        current_user=user, org=org,
    )


@router.post("/dzivoklis/submit")
async def submit(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Приём формы подачи показаний. Поля: value_<meter_id>=..."""
    org = _resident_org(session, user)
    period = current_period()
    form = await request.form()

    allowed_unit_ids = {u.id for u in units_for_user(session, user.id)}

    submitted, errors = 0, []
    for key, raw in form.items():
        if not key.startswith("value_"):
            continue
        raw = (raw or "").strip().replace(",", ".")
        if raw == "":
            continue
        meter_id = int(key.split("_", 1)[1])
        meter = session.get(Meter, meter_id)
        if not meter or meter.unit_id not in allowed_unit_ids:
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"Skaitītājs {meter.serial_number}: nederīga vērtība.")
            continue
        try:
            reading = upsert_reading(
                session, meter, value, period,
                submitted_by_id=user.id,
            )
            submitted += 1
            if reading.is_anomaly:
                flash(request,
                      f"Skaitītājs {meter.serial_number}: neparasti liels patēriņš "
                      f"({reading.consumption} {meter.meter_type.unit}). "
                      "Rādījums pieņemts, pārbaudiet ievadi.", "info")
        except ReadingValidationError as e:
            errors.append(f"Skaitītājs {meter.serial_number}: {e}")

    for e in errors:
        flash(request, e, "error")
    if submitted:
        flash(request, f"Nodoti {submitted} rādījumi par periodu {period}.", "success")
    elif not errors:
        flash(request, "Nav ievadīts neviens rādījums.", "info")

    return RedirectResponse("/dzivoklis", 303)
