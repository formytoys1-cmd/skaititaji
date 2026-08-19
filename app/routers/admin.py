"""Кабинет суперадмина платформы: организации, каталог типов счётчиков."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.auth import require_user
from app.database import get_session
from app.integrations.registry import get_integration
from app.models import (
    Building,
    MeterCategory,
    MeterType,
    Organization,
    Unit,
    User,
    UserRole,
)
from app.web import flash, render

router = APIRouter()


@router.get("/admin")
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if user.role != UserRole.SUPERADMIN:
        return RedirectResponse("/", 303)

    orgs = session.exec(select(Organization)).all()
    org_rows = []
    for o in orgs:
        n_buildings = session.exec(
            select(func.count(Building.id)).where(Building.organization_id == o.id)
        ).one()
        integration = get_integration(o)
        org_rows.append({
            "org": o,
            "buildings": n_buildings,
            "integration_ok": integration.health_check(),
            "mock": (o.integration_config or {}).get("mock", True),
        })

    meter_types = session.exec(
        select(MeterType).order_by(MeterType.sort_order)
    ).all()

    return render(
        request, "admin/dashboard.html",
        {"org_rows": org_rows, "meter_types": meter_types,
         "categories": [c.value for c in MeterCategory]},
        current_user=user,
    )


@router.post("/admin/meter-types")
def add_meter_type(
    request: Request,
    code: str = Form(...),
    name_lv: str = Form(...),
    name_ru: str = Form(...),
    name_en: str = Form(...),
    unit: str = Form("m³"),
    decimals: int = Form(3),
    icon: str = Form("💧"),
    color: str = Form("#0ea5e9"),
    category: str = Form("water"),
    max_plausible_consumption: float = Form(100.0),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Добавить новый тип счётчика — демонстрация расширяемости без кода."""
    if user.role != UserRole.SUPERADMIN:
        return RedirectResponse("/", 303)

    code = code.strip().lower().replace(" ", "_")
    existing = session.exec(select(MeterType).where(MeterType.code == code)).first()
    if existing:
        flash(request, f"Skaitītāja tips '{code}' jau eksistē.", "error")
        return RedirectResponse("/admin", 303)

    try:
        cat = MeterCategory(category)
    except ValueError:
        cat = MeterCategory.OTHER

    max_sort = session.exec(select(func.max(MeterType.sort_order))).one() or 0
    mt = MeterType(
        code=code, category=cat,
        name_lv=name_lv, name_ru=name_ru, name_en=name_en,
        unit=unit, decimals=decimals, icon=icon, color=color,
        max_plausible_consumption=max_plausible_consumption,
        sort_order=max_sort + 10,
    )
    session.add(mt)
    session.commit()
    flash(request, f"Pievienots jauns skaitītāja tips: {name_lv} ({code}).", "success")
    return RedirectResponse("/admin", 303)


@router.post("/admin/meter-types/{type_id}/toggle")
def toggle_meter_type(
    type_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if user.role != UserRole.SUPERADMIN:
        return RedirectResponse("/", 303)
    mt = session.get(MeterType, type_id)
    if mt:
        mt.is_active = not mt.is_active
        session.add(mt)
        session.commit()
    return RedirectResponse("/admin", 303)
