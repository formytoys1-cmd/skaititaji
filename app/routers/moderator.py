"""Консоль модератора: подача указаний агенту и переписка по ним.

Доступна суперадмину («админ учёта»). Модератор описывает, что нужно
переделать полностью или частично, и отправляет. Указание попадает агенту
(запущенной сессии) через watcher; агент отвечает здесь же.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlmodel import Session

from app.auth import require_user
from app.database import get_session
from app.feedback_service import (
    add_message,
    attachment_path,
    attachments_for_thread,
    create_thread,
    list_threads,
    messages_for,
    save_attachment,
    set_status,
)
from app.models import (
    FeedbackAttachment,
    FeedbackAuthor,
    FeedbackScope,
    FeedbackStatus,
    FeedbackThread,
    User,
    UserRole,
)
from app.web import flash, render

router = APIRouter()

STATUS_LABELS = {
    FeedbackStatus.NEW: ("Jauns", "amber"),
    FeedbackStatus.IN_PROGRESS: ("Darbā", "sky"),
    FeedbackStatus.NEEDS_CLARIFICATION: ("Gaida precizējumu", "purple"),
    FeedbackStatus.READY_FOR_REVIEW: ("Pārbaudei", "emerald"),
    FeedbackStatus.DONE: ("Pabeigts", "slate"),
    FeedbackStatus.REJECTED: ("Atcelts", "red"),
}


def _guard(user: User) -> bool:
    return user.role == UserRole.SUPERADMIN


async def _save_uploads(
    session: Session, thread_id: int, message_id: int | None,
    files: list[UploadFile] | None,
) -> int:
    """Сохраняет непустые загруженные файлы, возвращает их количество."""
    saved = 0
    for f in files or []:
        if not f or not f.filename:
            continue
        data = await f.read()
        if not data:
            continue
        save_attachment(
            session, thread_id, filename=f.filename, data=data,
            content_type=f.content_type, message_id=message_id,
        )
        saved += 1
    return saved


@router.get("/admin/inbox")
def inbox(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _guard(user):
        return RedirectResponse("/", 303)
    threads = list_threads(session)
    rows = []
    for t in threads:
        msgs = messages_for(session, t.id)
        atts = attachments_for_thread(session, t.id)
        rows.append({
            "thread": t,
            "count": len(msgs),
            "attachments": len(atts),
            "last": msgs[-1] if msgs else None,
            "status_label": STATUS_LABELS.get(t.status, (t.status.value, "slate")),
        })
    return render(
        request, "admin/inbox.html",
        {"rows": rows, "scopes": [s.value for s in FeedbackScope]},
        current_user=user,
    )


@router.post("/admin/inbox")
async def create(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    scope: str = Form("partial"),
    priority: str = Form("normal"),
    area: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _guard(user):
        return RedirectResponse("/", 303)
    try:
        sc = FeedbackScope(scope)
    except ValueError:
        sc = FeedbackScope.PARTIAL
    thread = create_thread(
        session, title=title, body=body, scope=sc,
        priority=priority, area=area, created_by=user.email,
    )
    first_msg = messages_for(session, thread.id)
    msg_id = first_msg[0].id if first_msg else None
    n = await _save_uploads(session, thread.id, msg_id, files)
    suffix = f" (+{n} fails)" if n else ""
    flash(request, f"Norādījums #{thread.id} nosūtīts aģentam{suffix}.", "success")
    return RedirectResponse(f"/admin/inbox/{thread.id}", 303)


@router.get("/admin/inbox/{thread_id}")
def thread_view(
    thread_id: int,
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _guard(user):
        return RedirectResponse("/", 303)
    thread = session.get(FeedbackThread, thread_id)
    if not thread:
        flash(request, "Norādījums nav atrasts.", "error")
        return RedirectResponse("/admin/inbox", 303)
    return render(
        request, "admin/inbox_thread.html",
        {
            "thread": thread,
            "messages": messages_for(session, thread_id),
            "attachments": attachments_for_thread(session, thread_id),
            "status_label": STATUS_LABELS.get(thread.status, (thread.status.value, "slate")),
        },
        current_user=user,
    )


@router.post("/admin/inbox/{thread_id}/reply")
async def reply(
    thread_id: int,
    request: Request,
    body: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _guard(user):
        return RedirectResponse("/", 303)
    msg_id = None
    if body.strip():
        msg = add_message(session, thread_id, FeedbackAuthor.MODERATOR, body)
        msg_id = msg.id
    n = await _save_uploads(session, thread_id, msg_id, files)
    if body.strip() or n:
        extra = f" (+{n} fails)" if n else ""
        flash(request, f"Ziņa nosūtīta aģentam{extra}.", "success")
    return RedirectResponse(f"/admin/inbox/{thread_id}", 303)


@router.get("/admin/inbox/attachment/{att_id}")
def download_attachment(
    att_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _guard(user):
        return RedirectResponse("/", 303)
    att = session.get(FeedbackAttachment, att_id)
    if not att:
        return RedirectResponse("/admin/inbox", 303)
    return FileResponse(
        attachment_path(att),
        filename=att.filename,
        media_type=att.content_type or "application/octet-stream",
    )


@router.post("/admin/inbox/{thread_id}/status")
def change_status(
    thread_id: int,
    request: Request,
    status: str = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _guard(user):
        return RedirectResponse("/", 303)
    try:
        st = FeedbackStatus(status)
        set_status(session, thread_id, st)
        flash(request, f"Statuss mainīts: {STATUS_LABELS.get(st, (status,))[0]}.", "success")
    except ValueError:
        flash(request, "Nederīgs statuss.", "error")
    return RedirectResponse(f"/admin/inbox/{thread_id}", 303)
