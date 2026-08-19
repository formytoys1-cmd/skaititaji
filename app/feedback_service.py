"""Сервис обратной связи: общая логика для веб-консоли модератора и CLI агента.

Машина состояний треда:
    new ──(агент берёт)──▶ in_progress
    in_progress ──(агент задаёт вопрос)──▶ needs_clarification
    needs_clarification ──(модератор отвечает)──▶ in_progress (снова требует внимания)
    in_progress ──(агент завершил)──▶ ready_for_review
    ready_for_review ──(модератор принял)──▶ done
    любой ──(модератор отменил)──▶ rejected

«Требует внимания агента» = последнее сообщение от модератора И статус активный.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import (
    FeedbackAttachment,
    FeedbackAuthor,
    FeedbackMessage,
    FeedbackScope,
    FeedbackStatus,
    FeedbackThread,
)

UPLOAD_DIR = os.path.join("data", "feedback_uploads")

ACTIVE_STATUSES = {
    FeedbackStatus.NEW,
    FeedbackStatus.IN_PROGRESS,
    FeedbackStatus.NEEDS_CLARIFICATION,
    FeedbackStatus.READY_FOR_REVIEW,
}


def create_thread(
    session: Session,
    *,
    title: str,
    body: str,
    scope: FeedbackScope = FeedbackScope.PARTIAL,
    priority: str = "normal",
    area: Optional[str] = None,
    created_by: Optional[str] = None,
) -> FeedbackThread:
    thread = FeedbackThread(
        title=title.strip(),
        scope=scope,
        priority=priority,
        area=(area or "").strip() or None,
        status=FeedbackStatus.NEW,
        created_by=created_by,
    )
    session.add(thread)
    session.commit()
    session.refresh(thread)
    add_message(session, thread.id, FeedbackAuthor.MODERATOR, body)
    return thread


def add_message(
    session: Session, thread_id: int, author: FeedbackAuthor, body: str
) -> FeedbackMessage:
    msg = FeedbackMessage(thread_id=thread_id, author=author, body=body.strip())
    session.add(msg)
    thread = session.get(FeedbackThread, thread_id)
    if thread:
        thread.updated_at = datetime.utcnow()
        # Ответ модератора возвращает тред в работу к агенту — даже если тред
        # был закрыт (done/rejected): новое сообщение снова требует внимания.
        if author == FeedbackAuthor.MODERATOR and thread.status in (
            FeedbackStatus.NEEDS_CLARIFICATION,
            FeedbackStatus.READY_FOR_REVIEW,
            FeedbackStatus.DONE,
            FeedbackStatus.REJECTED,
        ):
            thread.status = FeedbackStatus.IN_PROGRESS
        session.add(thread)
    session.commit()
    session.refresh(msg)
    return msg


def set_status(
    session: Session, thread_id: int, status: FeedbackStatus
) -> Optional[FeedbackThread]:
    thread = session.get(FeedbackThread, thread_id)
    if not thread:
        return None
    thread.status = status
    thread.updated_at = datetime.utcnow()
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return thread


def messages_for(session: Session, thread_id: int) -> list[FeedbackMessage]:
    return list(
        session.exec(
            select(FeedbackMessage)
            .where(FeedbackMessage.thread_id == thread_id)
            .order_by(FeedbackMessage.created_at, FeedbackMessage.id)
        ).all()
    )


def save_attachment(
    session: Session,
    thread_id: int,
    *,
    filename: str,
    data: bytes,
    content_type: Optional[str] = None,
    message_id: Optional[int] = None,
) -> FeedbackAttachment:
    """Сохраняет загруженный файл на диск и создаёт запись вложения."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_ext = os.path.splitext(filename)[1][:12]
    stored_name = f"{uuid.uuid4().hex}{safe_ext}"
    path = os.path.join(UPLOAD_DIR, stored_name)
    with open(path, "wb") as f:
        f.write(data)
    att = FeedbackAttachment(
        thread_id=thread_id,
        message_id=message_id,
        filename=filename,
        stored_name=stored_name,
        content_type=content_type,
        size=len(data),
    )
    session.add(att)
    session.commit()
    session.refresh(att)
    return att


def attachments_for_thread(
    session: Session, thread_id: int
) -> list[FeedbackAttachment]:
    return list(
        session.exec(
            select(FeedbackAttachment)
            .where(FeedbackAttachment.thread_id == thread_id)
            .order_by(FeedbackAttachment.created_at, FeedbackAttachment.id)
        ).all()
    )


def attachment_path(att: FeedbackAttachment) -> str:
    return os.path.join(UPLOAD_DIR, att.stored_name)


def list_threads(
    session: Session, only_active: bool = False
) -> list[FeedbackThread]:
    q = select(FeedbackThread).order_by(FeedbackThread.updated_at.desc())
    threads = list(session.exec(q).all())
    if only_active:
        threads = [t for t in threads if t.status in ACTIVE_STATUSES]
    return threads


def _last_message(session: Session, thread_id: int) -> Optional[FeedbackMessage]:
    return session.exec(
        select(FeedbackMessage)
        .where(FeedbackMessage.thread_id == thread_id)
        .order_by(FeedbackMessage.created_at.desc(), FeedbackMessage.id.desc())
    ).first()


def threads_awaiting_agent(session: Session) -> list[FeedbackThread]:
    """Треды, требующие внимания агента: активный статус и последнее слово за
    модератором (новое указание или ответ на уточнение)."""
    result = []
    for t in list_threads(session, only_active=True):
        last = _last_message(session, t.id)
        if t.status == FeedbackStatus.NEW:
            result.append(t)
        elif last and last.author == FeedbackAuthor.MODERATOR and t.status in (
            FeedbackStatus.IN_PROGRESS,
            FeedbackStatus.NEEDS_CLARIFICATION,
        ):
            result.append(t)
    # По приоритету, потом по дате
    prio = {"high": 0, "normal": 1, "low": 2}
    result.sort(key=lambda t: (prio.get(t.priority, 1), t.created_at))
    return result
