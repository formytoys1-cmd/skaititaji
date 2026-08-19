#!/usr/bin/env python
"""CLI агента для работы с обратной связью модератора.

Использование (из корня проекта, с активным venv):

  python -m tools.agent_feedback pending        # список тредов, требующих внимания
  python -m tools.agent_feedback show <id>      # показать тред целиком
  python -m tools.agent_feedback take <id>      # взять в работу (in_progress)
  python -m tools.agent_feedback reply <id> "текст ответа"     # ответить модератору
  python -m tools.agent_feedback ask  <id> "уточняющий вопрос" # запросить уточнение
  python -m tools.agent_feedback review <id> "что сделано"     # готово, на проверку
  python -m tools.agent_feedback done <id>      # закрыть (обычно делает модератор)

Все команды выводят JSON, чтобы агенту было удобно парсить.
"""
from __future__ import annotations

import json
import sys

from sqlmodel import Session

from app.database import engine, init_db
from app.feedback_service import (
    add_message,
    messages_for,
    set_status,
    threads_awaiting_agent,
)
from app.models import FeedbackAuthor, FeedbackStatus, FeedbackThread


def _thread_dict(session: Session, t: FeedbackThread, with_messages: bool = False):
    d = {
        "id": t.id,
        "title": t.title,
        "scope": t.scope.value,
        "priority": t.priority,
        "area": t.area,
        "status": t.status.value,
        "created_by": t.created_by,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }
    if with_messages:
        d["messages"] = [
            {
                "author": m.author.value,
                "body": m.body,
                "at": m.created_at.isoformat(),
            }
            for m in messages_for(session, t.id)
        ]
    return d


def cmd_pending(session: Session) -> None:
    threads = threads_awaiting_agent(session)
    out = [_thread_dict(session, t, with_messages=True) for t in threads]
    print(json.dumps({"count": len(out), "threads": out}, ensure_ascii=False, indent=2))


def cmd_show(session: Session, tid: int) -> None:
    t = session.get(FeedbackThread, tid)
    if not t:
        print(json.dumps({"error": "not found"})); return
    print(json.dumps(_thread_dict(session, t, with_messages=True), ensure_ascii=False, indent=2))


def cmd_take(session: Session, tid: int) -> None:
    set_status(session, tid, FeedbackStatus.IN_PROGRESS)
    print(json.dumps({"ok": True, "id": tid, "status": "in_progress"}, ensure_ascii=False))


def cmd_reply(session: Session, tid: int, body: str) -> None:
    add_message(session, tid, FeedbackAuthor.AGENT, body)
    print(json.dumps({"ok": True, "id": tid, "replied": True}, ensure_ascii=False))


def cmd_ask(session: Session, tid: int, body: str) -> None:
    add_message(session, tid, FeedbackAuthor.AGENT, body)
    set_status(session, tid, FeedbackStatus.NEEDS_CLARIFICATION)
    print(json.dumps({"ok": True, "id": tid, "status": "needs_clarification"}, ensure_ascii=False))


def cmd_review(session: Session, tid: int, body: str) -> None:
    add_message(session, tid, FeedbackAuthor.AGENT, body)
    set_status(session, tid, FeedbackStatus.READY_FOR_REVIEW)
    print(json.dumps({"ok": True, "id": tid, "status": "ready_for_review"}, ensure_ascii=False))


def cmd_done(session: Session, tid: int) -> None:
    set_status(session, tid, FeedbackStatus.DONE)
    print(json.dumps({"ok": True, "id": tid, "status": "done"}, ensure_ascii=False))


def main(argv: list[str]) -> int:
    init_db()
    if not argv:
        print(__doc__); return 1
    cmd = argv[0]
    with Session(engine) as session:
        if cmd == "pending":
            cmd_pending(session)
        elif cmd == "show" and len(argv) >= 2:
            cmd_show(session, int(argv[1]))
        elif cmd == "take" and len(argv) >= 2:
            cmd_take(session, int(argv[1]))
        elif cmd == "reply" and len(argv) >= 3:
            cmd_reply(session, int(argv[1]), argv[2])
        elif cmd == "ask" and len(argv) >= 3:
            cmd_ask(session, int(argv[1]), argv[2])
        elif cmd == "review" and len(argv) >= 3:
            cmd_review(session, int(argv[1]), argv[2])
        elif cmd == "done" and len(argv) >= 2:
            cmd_done(session, int(argv[1]))
        else:
            print(__doc__); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
