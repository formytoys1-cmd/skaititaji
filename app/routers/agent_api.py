"""Защищённый API агента для консоли обратной связи.

Позволяет запущенному агенту (сессии) удалённо читать треды модератора,
скачивать вложения и отвечать с авторством «агент» — в том числе на боевом
сервере, где нет прямого доступа к БД.

Все эндпоинты требуют заголовок ``X-Agent-Key`` со значением, равным
переменной окружения ``AGENT_API_KEY``. Если ключ не задан на сервере,
API отключён (503), чтобы случайно не открыть доступ.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.feedback_service import (
    add_message,
    attachment_path,
    attachments_for_thread,
    list_threads,
    messages_for,
    set_status,
)
from app.models import (
    FeedbackAttachment,
    FeedbackAuthor,
    FeedbackStatus,
    FeedbackThread,
)

router = APIRouter(prefix="/agent/api", tags=["agent"])


def require_agent(x_agent_key: str = Header(default="")) -> None:
    """Проверяет ключ агента. Отключает API, если ключ не сконфигурирован."""
    if not settings.agent_api_key:
        raise HTTPException(status_code=503, detail="Agent API disabled")
    if x_agent_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid agent key")


def _thread_summary(session: Session, t: FeedbackThread) -> dict:
    msgs = messages_for(session, t.id)
    atts = attachments_for_thread(session, t.id)
    return {
        "id": t.id,
        "title": t.title,
        "scope": t.scope.value,
        "priority": t.priority,
        "area": t.area,
        "status": t.status.value,
        "created_by": t.created_by,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "messages": len(msgs),
        "attachments": len(atts),
        "last_author": msgs[-1].author.value if msgs else None,
    }


@router.get("/threads")
def api_threads(
    only_active: bool = False,
    _: None = Depends(require_agent),
    session: Session = Depends(get_session),
) -> dict:
    threads = list_threads(session, only_active=only_active)
    return {"threads": [_thread_summary(session, t) for t in threads]}


@router.get("/threads/{thread_id}")
def api_thread(
    thread_id: int,
    _: None = Depends(require_agent),
    session: Session = Depends(get_session),
) -> dict:
    thread = session.get(FeedbackThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    msgs = messages_for(session, thread_id)
    atts = attachments_for_thread(session, thread_id)
    return {
        "thread": _thread_summary(session, thread),
        "messages": [
            {
                "id": m.id,
                "author": m.author.value,
                "body": m.body,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "content_type": a.content_type,
                "size": a.size,
                "message_id": a.message_id,
            }
            for a in atts
        ],
    }


@router.get("/attachment/{att_id}")
def api_attachment(
    att_id: int,
    _: None = Depends(require_agent),
    session: Session = Depends(get_session),
) -> dict:
    att = session.get(FeedbackAttachment, att_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    try:
        with open(attachment_path(att), "rb") as f:
            data = f.read()
    except FileNotFoundError:
        # На эфемерной ФС (Render) файл мог быть утерян после рестарта.
        raise HTTPException(status_code=410, detail="Attachment file gone")
    return {
        "id": att.id,
        "filename": att.filename,
        "content_type": att.content_type,
        "size": att.size,
        "base64": base64.b64encode(data).decode("ascii"),
    }


# Ответ агента может опционально переводить тред в статус.
_STATUS_ACTIONS = {
    "review": FeedbackStatus.READY_FOR_REVIEW,
    "ask": FeedbackStatus.NEEDS_CLARIFICATION,
    "progress": FeedbackStatus.IN_PROGRESS,
    "done": FeedbackStatus.DONE,
}


@router.post("/threads/{thread_id}/reply")
def api_reply(
    thread_id: int,
    payload: dict,
    _: None = Depends(require_agent),
    session: Session = Depends(get_session),
) -> dict:
    thread = session.get(FeedbackThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=422, detail="Empty body")
    msg = add_message(session, thread_id, FeedbackAuthor.AGENT, body)
    action = (payload.get("status") or "").strip().lower()
    new_status = _STATUS_ACTIONS.get(action)
    if new_status:
        set_status(session, thread_id, new_status)
    return {
        "ok": True,
        "message_id": msg.id,
        "status": (new_status.value if new_status else thread.status.value),
    }
