"""Консоль модератора: подача указаний агенту и переписка по ним.

Доступна суперадмину («админ учёта»). Модератор описывает, что нужно
переделать полностью или частично, и отправляет. Указание попадает агенту
(запущенной сессии) через watcher; агент отвечает здесь же.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.auth import require_user
from app.database import get_session
from app.feedback_service import (
    add_message,
    create_thread,
    list_threads,
    messages_for,
    set_status,
)
from app.models import (
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
        rows.append({
            "thread": t,
            "count": len(msgs),
            "last": msgs[-1] if msgs else None,
            "status_label": STATUS_LABELS.get(t.status, (t.status.value, "slate")),
        })
    return render(
        request, "admin/inbox.html",
        {"rows": rows, "scopes": [s.value for s in FeedbackScope]},
        current_user=user,
    )


@router.post("/admin/inbox")
def create(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    scope: str = Form("partial"),
    priority: str = Form("normal"),
    area: str = Form(""),
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
    flash(request, f"Norādījums #{thread.id} nosūtīts aģentam.", "success")
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
            "status_label": STATUS_LABELS.get(thread.status, (thread.status.value, "slate")),
        },
        current_user=user,
    )


@router.post("/admin/inbox/{thread_id}/reply")
def reply(
    thread_id: int,
    request: Request,
    body: str = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    if not _guard(user):
        return RedirectResponse("/", 303)
    if body.strip():
        add_message(session, thread_id, FeedbackAuthor.MODERATOR, body)
        flash(request, "Ziņa nosūtīta aģentam.", "success")
    return RedirectResponse(f"/admin/inbox/{thread_id}", 303)


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
