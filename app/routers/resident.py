"""Кабинет жителя: просмотр квартир, счётчиков и подача показаний."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlmodel import Session

from app.auth import require_user
from app.csrf import csrf_protect
from app.database import get_session
from app.i18n import t as i18n_t
from app.models import Meter, Organization, ReadingSource, User, UserRole
from app.photo_ocr import PhotoOCRError, PhotoOCRResult, recognize_meter_photo
from app.services import (
    ReadingValidationError,
    average_consumption,
    current_period,
    is_window_open,
    last_reading,
    meters_for_unit,
    reading_for_period,
    readings_history,
    units_for_user,
    upsert_reading,
    window_status,
)
from app.web import current_lang, flash, render

router = APIRouter()
MAX_PHOTO_FILES = 10
MAX_PHOTO_BYTES = 8 * 1024 * 1024


def _resident_org(session: Session, user: User) -> Organization | None:
    if user.organization_id:
        return session.get(Organization, user.organization_id)
    return None


def _resident_meters(session: Session, user: User) -> list[dict]:
    rows = []
    for unit in units_for_user(session, user.id):
        for meter in meters_for_unit(session, unit.id):
            prev = last_reading(session, meter.id)
            prev_value = prev.value if prev else meter.initial_value
            rows.append({
                "id": meter.id,
                "label": f"{unit.number} · {meter.serial_number}",
                "unit": meter.meter_type.unit if meter.meter_type else "",
                "prev_value": prev_value,
            })
    return rows


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
    win = window_status(org) if org else None

    unit_cards = []
    for unit in units:
        meters = meters_for_unit(session, unit.id)
        meter_rows = []
        for m in meters:
            prev = last_reading(session, m.id)
            this_period = reading_for_period(session, m.id, period)
            avg = average_consumption(session, m.id)
            meter_rows.append({
                "meter": m,
                "type": m.meter_type,
                "prev": prev,
                "prev_value": prev.value if prev else m.initial_value,
                "current": this_period,
                "avg_consumption": avg,
            })
        unit_cards.append({"unit": unit, "meters": meter_rows})

    return render(
        request, "resident/dashboard.html",
        {
            "unit_cards": unit_cards,
            "period": period,
            "window_open": window_open,
            "win": win,
        },
        current_user=user, org=org,
    )


@router.post("/dzivoklis/submit")
async def submit(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    """Приём формы подачи показаний. Поля: value_<meter_id>=..."""
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
                submitted_by_id=user.id, actor_id=user.id,
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


@router.post("/dzivoklis/photo/recognize")
async def recognize_from_photos(
    request: Request,
    photos: list[UploadFile] = File(default=[]),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    if user.role != UserRole.RESIDENT:
        return RedirectResponse("/", 303)

    lang = current_lang(request)
    meter_options = _resident_meters(session, user)
    if not meter_options:
        flash(request, i18n_t(lang, "res.photo_no_meters"), "error")
        return RedirectResponse("/dzivoklis", 303)
    if not photos:
        flash(request, i18n_t(lang, "res.photo_no_files"), "error")
        return RedirectResponse("/dzivoklis", 303)
    if len(photos) > MAX_PHOTO_FILES:
        flash(
            request,
            i18n_t(lang, "res.photo_too_many").format(max_files=MAX_PHOTO_FILES),
            "error",
        )
        return RedirectResponse("/dzivoklis", 303)

    results: list[dict] = []
    for idx, photo in enumerate(photos):
        if not photo.filename:
            continue
        content_type = photo.content_type or ""
        if content_type and not content_type.startswith("image/"):
            results.append({
                "idx": idx,
                "filename": photo.filename,
                "ocr": PhotoOCRResult(
                    value=None,
                    candidates=[],
                    raw_text="",
                    provider="validation",
                    warning=i18n_t(lang, "res.photo_not_image"),
                ),
            })
            continue

        data = await photo.read()
        if not data:
            continue
        if len(data) > MAX_PHOTO_BYTES:
            results.append({
                "idx": idx,
                "filename": photo.filename,
                "ocr": PhotoOCRResult(
                    value=None,
                    candidates=[],
                    raw_text="",
                    provider="validation",
                    warning=i18n_t(lang, "res.photo_too_large").format(
                        max_mb=MAX_PHOTO_BYTES // (1024 * 1024)
                    ),
                ),
            })
            continue
        try:
            ocr = await recognize_meter_photo(
                filename=photo.filename,
                data=data,
                content_type=content_type or "application/octet-stream",
            )
        except PhotoOCRError as exc:
            ocr = PhotoOCRResult(
                value=None,
                candidates=[],
                raw_text="",
                provider="ocr",
                warning=str(exc),
            )
        results.append({"idx": idx, "filename": photo.filename, "ocr": ocr})

    if not results:
        flash(request, i18n_t(lang, "res.photo_no_files"), "error")
        return RedirectResponse("/dzivoklis", 303)

    org = _resident_org(session, user)
    return render(
        request,
        "resident/photo_review.html",
        {
            "period": current_period(),
            "rows": results,
            "meter_options": meter_options,
        },
        current_user=user,
        org=org,
    )


@router.post("/dzivoklis/photo/confirm")
async def confirm_photo_readings(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    if user.role != UserRole.RESIDENT:
        return RedirectResponse("/", 303)

    lang = current_lang(request)
    period = current_period()
    form = await request.form()
    meter_map = {m["id"]: m for m in _resident_meters(session, user)}

    submitted, errors = 0, []
    for row_id in form.getlist("row_ids"):
        if form.get(f"confirm_{row_id}") != "1":
            continue
        meter_raw = (form.get(f"meter_{row_id}") or "").strip()
        value_raw = (form.get(f"value_{row_id}") or "").strip().replace(",", ".")
        if not meter_raw or not value_raw:
            errors.append(i18n_t(lang, "res.photo_missing_data"))
            continue
        try:
            meter_id = int(meter_raw)
            value = float(value_raw)
        except ValueError:
            errors.append(i18n_t(lang, "res.photo_bad_value"))
            continue
        if meter_id not in meter_map:
            errors.append(i18n_t(lang, "res.photo_meter_forbidden"))
            continue
        meter = session.get(Meter, meter_id)
        if not meter:
            errors.append(i18n_t(lang, "res.photo_meter_missing"))
            continue
        try:
            upsert_reading(
                session,
                meter,
                value,
                period,
                submitted_by_id=user.id,
                actor_id=user.id,
            )
            submitted += 1
        except ReadingValidationError as exc:
            errors.append(f"{meter.serial_number}: {exc}")

    for err in errors:
        flash(request, err, "error")
    if submitted:
        flash(
            request,
            i18n_t(lang, "res.photo_saved").format(count=submitted, period=period),
            "success",
        )
    elif not errors:
        flash(request, i18n_t(lang, "res.photo_nothing_confirmed"), "info")

    return RedirectResponse("/dzivoklis", 303)


@router.get("/dzivoklis/vesture")
def history(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """История показаний и график расхода по каждому счётчику жителя."""
    if user.role != UserRole.RESIDENT:
        return RedirectResponse("/", 303)

    org = _resident_org(session, user)
    units = units_for_user(session, user.id)
    unit_cards = []
    for unit in units:
        meter_rows = []
        for m in meters_for_unit(session, unit.id):
            rows = readings_history(session, m.id, limit=12)
            points = [
                {
                    "period": r.period,
                    "value": r.value,
                    "consumption": r.consumption or 0.0,
                    "estimated": r.source == ReadingSource.ESTIMATED,
                }
                for r in rows
            ]
            max_c = max((p["consumption"] for p in points), default=0.0)
            meter_rows.append({
                "meter": m,
                "type": m.meter_type,
                "points": points,
                "max_c": max_c,
                "avg": average_consumption(session, m.id),
            })
        unit_cards.append({"unit": unit, "meters": meter_rows})

    return render(
        request, "resident/history.html",
        {"unit_cards": unit_cards},
        current_user=user, org=org,
    )


@router.get("/dzivoklis/druka")
def print_form(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Печатная форма подачи, повторяющая структуру бумажного счёта."""
    if user.role != UserRole.RESIDENT:
        return RedirectResponse("/", 303)

    org = _resident_org(session, user)
    units = units_for_user(session, user.id)
    period = current_period()
    unit_cards = []
    for unit in units:
        meter_rows = []
        for m in meters_for_unit(session, unit.id):
            prev = last_reading(session, m.id)
            this_period = reading_for_period(session, m.id, period)
            meter_rows.append({
                "meter": m,
                "type": m.meter_type,
                "prev_value": prev.value if prev else m.initial_value,
                "current": this_period,
            })
        unit_cards.append({"unit": unit, "meters": meter_rows})

    return render(
        request, "resident/print_form.html",
        {"unit_cards": unit_cards, "period": period},
        current_user=user, org=org,
    )


@router.get("/dzivoklis/vesture/export.csv")
def history_csv(
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Экспорт полной истории показаний жителя в CSV (Excel-совместимый)."""
    if user.role != UserRole.RESIDENT:
        return RedirectResponse("/", 303)

    def rows():
        # BOM для корректной кириллицы/диакритики в Excel + заголовок.
        yield "\ufeff"
        header = [
            "Dzivoklis", "Konts", "Skaititajs_Nr", "Tips",
            "Periods", "Radijums", "Paterins", "Vieniba",
            "Datums", "Avots",
        ]
        yield ";".join(header) + "\r\n"
        for unit in units_for_user(session, user.id):
            for m in meters_for_unit(session, unit.id):
                mtype = m.meter_type
                for r in readings_history(session, m.id, limit=120):
                    row = [
                        unit.number or "",
                        unit.account_number or "",
                        m.serial_number or "",
                        (mtype.name_lv if mtype else ""),
                        r.period,
                        f"{r.value:.3f}",
                        (f"{r.consumption:.3f}" if r.consumption is not None else ""),
                        (mtype.unit if mtype else ""),
                        r.reading_date.strftime("%Y-%m-%d") if r.reading_date else "",
                        r.source.value,
                    ]
                    # экранируем разделитель/кавычки на всякий случай
                    safe = ['"' + c.replace('"', '""') + '"' if (";" in c or '"' in c) else c
                            for c in row]
                    yield ";".join(safe) + "\r\n"

    filename = f"skaititaji_vesture_{current_period()}.csv"
    return StreamingResponse(
        rows(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
