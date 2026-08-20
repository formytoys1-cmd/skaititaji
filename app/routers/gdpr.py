"""GDPR-001 — HTTP-эндпоинты прав субъекта данных (экспорт и удаление).

- `GET  /gdpr/export/{subject_id}` — экспорт данных субъекта (JSON).
- `POST /gdpr/erase/{subject_id}`  — удаление/анонимизация данных субъекта.

Доступ ограничен `authorize_subject_access`: субъект — только к своим данным,
управляющий — по субъектам своей организации, суперадмин — глобально.
Удаление доступно только субъекту и суперадмину/управляющему по своей организации
и логируется в audit_log (OPS-001).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.audit import record_audit
from app.auth import require_user
from app.csrf import csrf_protect
from app.database import get_session
from app.gdpr import (
    GdprAccessError,
    authorize_subject_access,
    erase_subject,
    export_subject_data,
)
from app.models import User

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


def _authorize(session: Session, requester: User, subject_id: int) -> User:
    subject = session.get(User, subject_id)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subjekts nav atrasts.")
    try:
        authorize_subject_access(requester, subject)
    except GdprAccessError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    return subject


@router.get("/export/{subject_id}")
def export(
    subject_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    _authorize(session, user, subject_id)
    return JSONResponse(export_subject_data(session, subject_id))


@router.post("/erase/{subject_id}")
def erase(
    subject_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    _authorize(session, user, subject_id)
    summary = erase_subject(session, subject_id)
    record_audit(
        session,
        actor_id=user.id,
        action="gdpr_erase",
        entity_type="user",
        entity_id=subject_id,
        old_value=None,
        new_value=summary,
    )
    return JSONResponse({"status": "erased", **summary})
