"""Кабинет управляющего (apsaimniekotājs): контроль подачи, аномалии, выгрузка."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlmodel import Session, select

from app.audit import record_audit
from app.auth import require_user
from app.csrf import csrf_protect
from app.database import get_session
from app.integrations.registry import get_integration
from app.models import (
    Building,
    IntegrationLog,
    Meter,
    Organization,
    Reading,
    ReadingStatus,
    Unit,
    User,
    UserRole,
)
from app.services import current_period, window_status
from app.web import flash, render

router = APIRouter()


def _require_manager(user: User) -> bool:
    return user.role in (UserRole.MANAGER, UserRole.SUPERADMIN)


def _manager_org(session: Session, user: User) -> Organization | None:
    if not _require_manager(user):
        return None
    if user.organization_id:
        return session.get(Organization, user.organization_id)
    return session.exec(select(Organization)).first()


@router.get("/parvalde/iestatijumi")
def settings_form(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)
    return render(request, "manager/settings.html",
                  {"win": window_status(org)}, current_user=user, org=org)


@router.post("/parvalde/iestatijumi")
def settings_submit(
    request: Request,
    reading_day_from: str = Form(...),
    reading_day_to: str = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    org = _manager_org(session, user)
    if not org:
        return RedirectResponse("/", 303)

    def _day(v: str, default: int) -> int:
        try:
            n = int(str(v).strip())
        except (ValueError, TypeError):
            return default
        return min(28, max(1, n))  # 1..28, чтобы день существовал в любом месяце

    org.reading_day_from = _day(reading_day_from, org.reading_day_from)
    org.reading_day_to = _day(reading_day_to, org.reading_day_to)
    session.add(org)
    session.commit()
    flash(request, "Nodošanas periods saglabāts.", "success")
    return RedirectResponse("/parvalde/iestatijumi", 303)


@router.get("/parvalde")
def dashboard(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _require_manager(user):
        return RedirectResponse("/", 303)

    org = session.get(Organization, user.organization_id) if user.organization_id else \
        session.exec(select(Organization)).first()
    period = current_period()

    buildings = session.exec(
        select(Building).where(Building.organization_id == org.id)
    ).all()
    building_ids = [b.id for b in buildings]
    units = session.exec(
        select(Unit).where(Unit.building_id.in_(building_ids))
    ).all() if building_ids else []
    unit_ids = [u.id for u in units]
    meters = session.exec(
        select(Meter).where(Meter.unit_id.in_(unit_ids))
    ).all() if unit_ids else []
    meter_ids = [m.id for m in meters]

    period_readings = session.exec(
        select(Reading).where(
            Reading.meter_id.in_(meter_ids), Reading.period == period
        )
    ).all() if meter_ids else []

    submitted_meter_ids = {r.meter_id for r in period_readings}
    anomalies = [r for r in period_readings if r.is_anomaly]
    not_synced = [r for r in period_readings if r.status != ReadingStatus.SYNCED]

    stats = {
        "buildings": len(buildings),
        "units": len(units),
        "meters": len(meters),
        "submitted": len(submitted_meter_ids),
        "pending": len(meters) - len(submitted_meter_ids),
        "progress": round(100 * len(submitted_meter_ids) / len(meters)) if meters else 0,
        "anomalies": len(anomalies),
        "not_synced": len(not_synced),
    }

    # Детализация по счётчикам (для таблицы)
    unit_by_id = {u.id: u for u in units}
    reading_by_meter = {r.meter_id: r for r in period_readings}
    rows = []
    for m in meters:
        r = reading_by_meter.get(m.id)
        rows.append({
            "meter": m,
            "unit": unit_by_id.get(m.unit_id),
            "type": m.meter_type,
            "reading": r,
        })
    rows.sort(key=lambda x: (x["reading"] is not None, ))

    logs = session.exec(
        select(IntegrationLog)
        .where(IntegrationLog.organization_id == org.id)
        .order_by(IntegrationLog.created_at.desc())
    ).all()

    return render(
        request, "manager/dashboard.html",
        {
            "stats": stats, "period": period, "rows": rows,
            "anomalies": anomalies, "logs": logs[:10],
        },
        current_user=user, org=org,
    )


@router.get("/parvalde/eksports.csv")
def manager_export(
    period: str | None = None,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """CSV-выгрузка показаний по всем счётчикам организации за период.

    Удобно для бухгалтерии/сверки перед выгрузкой в Visma Horizon. По умолчанию
    — текущий период; можно указать ?period=YYYY-MM.
    """
    if not _require_manager(user):
        return RedirectResponse("/", 303)

    org = session.get(Organization, user.organization_id) if user.organization_id else \
        session.exec(select(Organization)).first()
    per = period or current_period()

    building_ids = [b.id for b in session.exec(
        select(Building).where(Building.organization_id == org.id)).all()]
    units = session.exec(
        select(Unit).where(Unit.building_id.in_(building_ids))).all() if building_ids else []
    unit_by_id = {u.id: u for u in units}
    unit_ids = list(unit_by_id.keys())
    meters = session.exec(
        select(Meter).where(Meter.unit_id.in_(unit_ids))).all() if unit_ids else []
    meter_ids = [m.id for m in meters]
    readings = session.exec(
        select(Reading).where(
            Reading.meter_id.in_(meter_ids), Reading.period == per)
    ).all() if meter_ids else []
    reading_by_meter = {r.meter_id: r for r in readings}

    def rows():
        yield "\ufeff"
        header = [
            "Dzivoklis", "Konts", "Skaititajs_Nr", "Tips", "Periods",
            "Radijums", "Paterins", "Vieniba", "Datums", "Statuss",
            "Anomalija", "Avots", "Iesniegts",
        ]
        yield ";".join(header) + "\r\n"
        for m in meters:
            unit = unit_by_id.get(m.unit_id)
            mtype = m.meter_type
            r = reading_by_meter.get(m.id)
            row = [
                (unit.number if unit else ""),
                (unit.account_number if unit else ""),
                m.serial_number or "",
                (mtype.name_lv if mtype else ""),
                per,
                (f"{r.value:.3f}" if r else ""),
                (f"{r.consumption:.3f}" if (r and r.consumption is not None) else ""),
                (mtype.unit if mtype else ""),
                (r.reading_date.strftime("%Y-%m-%d") if (r and r.reading_date) else ""),
                (r.status.value if r else "nav_iesniegts"),
                ("ja" if (r and r.is_anomaly) else ""),
                (r.source.value if r else ""),
                ("ja" if r else "ne"),
            ]
            safe = ['"' + c.replace('"', '""') + '"' if (";" in c or '"' in c) else c
                    for c in row]
            yield ";".join(safe) + "\r\n"

    filename = f"skaititaji_parvalde_{per}.csv"
    return StreamingResponse(
        rows(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/parvalde/sync")
def sync_to_visma(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    """Выгрузить принятые показания текущего периода в Visma Horizon."""
    if not _require_manager(user):
        return RedirectResponse("/", 303)

    org = session.get(Organization, user.organization_id) if user.organization_id else \
        session.exec(select(Organization)).first()
    period = current_period()

    building_ids = [b.id for b in session.exec(
        select(Building).where(Building.organization_id == org.id)).all()]
    unit_ids = [u.id for u in session.exec(
        select(Unit).where(Unit.building_id.in_(building_ids))).all()] if building_ids else []
    meters = session.exec(
        select(Meter).where(Meter.unit_id.in_(unit_ids))).all() if unit_ids else []
    meter_by_id = {m.id: m for m in meters}
    meter_ids = list(meter_by_id)

    to_sync = session.exec(
        select(Reading).where(
            Reading.meter_id.in_(meter_ids),
            Reading.period == period,
            Reading.status != ReadingStatus.SYNCED,
        )
    ).all() if meter_ids else []

    if not to_sync:
        flash(request, "Nav jaunu rādījumu ko sinhronizēt.", "info")
        return RedirectResponse("/parvalde", 303)

    payload = [
        {
            "external_meter_id": meter_by_id[r.meter_id].external_id
            or str(meter_by_id[r.meter_id].id),
            "value": r.value,
            "reading_date": r.reading_date.isoformat(),
            "period": r.period,
        }
        for r in to_sync
    ]

    integration = get_integration(org)
    result = integration.push_readings(payload)

    log = IntegrationLog(
        organization_id=org.id,
        provider=org.integration_provider,
        action="push_readings",
        status="ok" if result.ok else "error",
        message=result.message,
        payload={"count": result.pushed, "external_ids": result.external_ids},
    )
    session.add(log)

    if result.ok:
        for r, ext in zip(to_sync, result.external_ids + [None] * len(to_sync)):
            old_status = r.status.value
            r.status = ReadingStatus.SYNCED
            r.synced_at = datetime.utcnow()
            if ext:
                r.external_id = ext
            session.add(r)
            record_audit(
                session,
                actor_id=user.id,
                action="reading_status_change",
                entity_type="reading",
                entity_id=r.id,
                old_value={"status": old_status},
                new_value={"status": ReadingStatus.SYNCED.value},
                commit=False,
            )
        flash(request, result.message, "success")
    else:
        flash(request, f"Sinhronizācijas kļūda: {result.message}", "error")

    session.commit()
    return RedirectResponse("/parvalde", 303)
