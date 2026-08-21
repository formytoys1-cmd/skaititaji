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
from app.config import settings
from app.csrf import csrf_protect
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
    _csrf: None = Depends(csrf_protect),
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
    _csrf: None = Depends(csrf_protect),
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


@router.post("/parvalde/objekti/{building_id}/generate")
def generate_units(
    building_id: int,
    request: Request,
    entrances: str = Form("1"),
    floors: str = Form(...),
    per_floor: str = Form(...),
    start_number: str = Form("1"),
    max_residents: str = Form(""),
    account_prefix: str = Form(""),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    """Массовая генерация квартир для дома.

    Пример (119-я серия, Islices 3): 2 подъезда × 10 этажей × 4 кв/этаж = 80
    квартир, нумерация сквозная от start_number. Каждой квартире присваивается
    лицевой счёт (account_number) для самрегистрации жителя и вместимость
    max_residents (запас ×2). Уже существующие номера пропускаются.
    """
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    b = _owned_building(session, org, building_id)
    if not b:
        return RedirectResponse("/parvalde/objekti", 303)

    def _int(v: str, default: int = 0) -> int:
        try:
            return int(str(v).strip())
        except (ValueError, TypeError):
            return default

    n_entr = max(1, _int(entrances, 1))
    n_floors = max(1, _int(floors, 0))
    n_per = max(1, _int(per_floor, 0))
    start = max(1, _int(start_number, 1))
    cap = _int(max_residents, settings.default_unit_capacity)
    if cap < 0:
        cap = settings.default_unit_capacity
    total = n_entr * n_floors * n_per

    # Защита от абсурдных объёмов (случайных/злонамеренных).
    if total <= 0 or total > 2000:
        flash(request, "Nederīgs dzīvokļu skaits (1–2000).", "error")
        return RedirectResponse(f"/parvalde/objekti/{building_id}", 303)

    existing = {
        (row.number or "").strip()
        for row in session.exec(select(Unit).where(Unit.building_id == b.id)).all()
    }
    prefix = account_prefix.strip() or f"LV-{b.id}-"
    created = 0
    for i in range(total):
        num = str(start + i)
        if num in existing:
            continue
        session.add(Unit(
            building_id=b.id, number=num,
            account_number=f"{prefix}{num}",
            max_residents=cap,
        ))
        created += 1
    session.commit()
    flash(request,
          f"Izveidoti {created} dzīvokļi (izlaisti {total - created} jau esošie).",
          "success")
    return RedirectResponse(f"/parvalde/objekti/{building_id}", 303)


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
    _csrf: None = Depends(csrf_protect),
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
