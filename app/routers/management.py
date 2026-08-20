"""Управление структурой недвижимости управляющим (без seed).

Позволяет apsaimniekotājs из UI завести дома → квартиры → счётчики, чтобы
платформу можно было реально внедрить в организацию без правки кода.
Строгая изоляция по организации (multi-tenant): управляющий видит только
объекты своей организации.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.auth import require_user
from app.database import get_session
from app.models import (
    Building,
    Meter,
    MeterType,
    Organization,
    Unit,
    User,
    UserRole,
)
from app.tenancy import owned_building as _owned_building
from app.tenancy import owned_unit as _owned_unit
from app.web import flash, render

router = APIRouter()


def _manager_org(session: Session, user: User) -> Organization | None:
    if user.role not in (UserRole.MANAGER, UserRole.SUPERADMIN):
        return None
    if user.organization_id:
        return session.get(Organization, user.organization_id)
    return session.exec(select(Organization)).first()


# --------------------------------------------------------------------------- #
# Дома
# --------------------------------------------------------------------------- #
@router.get("/parvalde/objekti")
def buildings(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    rows = []
    for b in session.exec(
        select(Building).where(Building.organization_id == org.id)
        .order_by(Building.id)
    ).all():
        n_units = session.exec(
            select(func.count(Unit.id)).where(Unit.building_id == b.id)
        ).one()
        rows.append({"building": b, "units": n_units})
    return render(request, "manager/buildings.html", {"rows": rows},
                  current_user=user, org=org)


@router.post("/parvalde/objekti")
def create_building(
    request: Request,
    address: str = Form(...),
    name: str = Form(""),
    external_id: str = Form(""),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    if not address.strip():
        flash(request, "Adrese ir obligāta.", "error")
        return RedirectResponse("/parvalde/objekti", 303)
    b = Building(organization_id=org.id, address=address.strip(),
                 name=name.strip() or None, external_id=external_id.strip() or None)
    session.add(b)
    session.commit()
    flash(request, "Māja pievienota.", "success")
    return RedirectResponse(f"/parvalde/objekti/{b.id}", 303)


# --------------------------------------------------------------------------- #
# Квартиры внутри дома
# --------------------------------------------------------------------------- #
@router.get("/parvalde/objekti/{building_id}")
def building_detail(
    building_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    b = _owned_building(session, org, building_id)
    if not b:
        flash(request, "Māja nav atrasta.", "error")
        return RedirectResponse("/parvalde/objekti", 303)
    rows = []
    for u in session.exec(
        select(Unit).where(Unit.building_id == b.id).order_by(Unit.id)
    ).all():
        n_meters = session.exec(
            select(func.count(Meter.id)).where(Meter.unit_id == u.id)
        ).one()
        rows.append({"unit": u, "meters": n_meters})
    return render(request, "manager/building_detail.html",
                  {"building": b, "rows": rows}, current_user=user, org=org)


@router.post("/parvalde/objekti/{building_id}/units")
def create_unit(
    building_id: int,
    request: Request,
    number: str = Form(...),
    account_number: str = Form(""),
    area_m2: str = Form(""),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    b = _owned_building(session, org, building_id)
    if not b:
        return RedirectResponse("/parvalde/objekti", 303)
    if not number.strip():
        flash(request, "Dzīvokļa numurs ir obligāts.", "error")
        return RedirectResponse(f"/parvalde/objekti/{building_id}", 303)
    try:
        area = float(area_m2.replace(",", ".")) if area_m2.strip() else None
    except ValueError:
        area = None
    u = Unit(building_id=b.id, number=number.strip(),
             account_number=account_number.strip() or None, area_m2=area)
    session.add(u)
    session.commit()
    flash(request, "Dzīvoklis pievienots.", "success")
    return RedirectResponse(f"/parvalde/dzivoklis/{u.id}", 303)


# --------------------------------------------------------------------------- #
# Счётчики внутри квартиры
# --------------------------------------------------------------------------- #
@router.get("/parvalde/dzivoklis/{unit_id}")
def unit_detail(
    unit_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    u = _owned_unit(session, org, unit_id)
    if not u:
        flash(request, "Dzīvoklis nav atrasts.", "error")
        return RedirectResponse("/parvalde/objekti", 303)
    building = session.get(Building, u.building_id)
    meters = session.exec(
        select(Meter).where(Meter.unit_id == u.id).order_by(Meter.id)
    ).all()
    meter_types = session.exec(
        select(MeterType).where(MeterType.is_active == True)  # noqa: E712
        .order_by(MeterType.sort_order)
    ).all()
    return render(request, "manager/unit_detail.html",
                  {"unit": u, "building": building, "meters": meters,
                   "meter_types": meter_types},
                  current_user=user, org=org)


@router.post("/parvalde/dzivoklis/{unit_id}/meters")
def create_meter(
    unit_id: int,
    request: Request,
    meter_type_id: int = Form(...),
    serial_number: str = Form(...),
    location: str = Form(""),
    initial_value: str = Form("0"),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    u = _owned_unit(session, org, unit_id)
    if not u:
        return RedirectResponse("/parvalde/objekti", 303)
    mt = session.get(MeterType, meter_type_id)
    if not mt:
        flash(request, "Nederīgs skaitītāja tips.", "error")
        return RedirectResponse(f"/parvalde/dzivoklis/{unit_id}", 303)
    if not serial_number.strip():
        flash(request, "Skaitītāja numurs ir obligāts.", "error")
        return RedirectResponse(f"/parvalde/dzivoklis/{unit_id}", 303)
    try:
        init = float(initial_value.replace(",", ".")) if initial_value.strip() else 0.0
    except ValueError:
        init = 0.0
    m = Meter(unit_id=u.id, meter_type_id=mt.id, serial_number=serial_number.strip(),
              location=location.strip() or None, initial_value=init,
              installed_on=date.today())
    session.add(m)
    session.commit()
    flash(request, "Skaitītājs pievienots.", "success")
    return RedirectResponse(f"/parvalde/dzivoklis/{unit_id}", 303)
