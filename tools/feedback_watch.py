#!/usr/bin/env python
"""Watcher-мост: связывает веб-консоль модератора с запущенным агентом.

Как это работает:
1. Модератор отправляет указание через веб-консоль (/admin/inbox).
2. Указание сохраняется в БД приложения.
3. Этот скрипт запускается агентом в фоне и периодически опрашивает БД.
4. Как только появляется тред, требующий внимания агента (новое указание или
   ответ модератора), скрипт печатает его как JSON и завершается.
5. Среда уведомляет агента о завершении фоновой команды; агент читает вывод,
   обрабатывает указание (правит сайт), отвечает через tools.agent_feedback и
   снова запускает watcher.

Параметры окружения:
  FB_POLL_INTERVAL  — интервал опроса, сек (по умолчанию 5)
  FB_MAX_WAIT       — максимальное время ожидания, сек (0 = бесконечно; по умолч. 0)
"""
from __future__ import annotations

import json
import os
import time

from sqlmodel import Session

from app.database import engine, init_db
from app.feedback_service import messages_for, threads_awaiting_agent


def snapshot(session: Session) -> list[dict]:
    threads = threads_awaiting_agent(session)
    out = []
    for t in threads:
        msgs = messages_for(session, t.id)
        out.append({
            "id": t.id,
            "title": t.title,
            "scope": t.scope.value,
            "priority": t.priority,
            "area": t.area,
            "status": t.status.value,
            "created_by": t.created_by,
            "messages": [
                {"author": m.author.value, "body": m.body,
                 "at": m.created_at.isoformat()} for m in msgs
            ],
        })
    return out


def main() -> int:
    init_db()
    interval = float(os.getenv("FB_POLL_INTERVAL", "5"))
    max_wait = float(os.getenv("FB_MAX_WAIT", "0"))
    started = time.time()

    print(f"[watch] Слежу за обратной связью (интервал {interval}s). Ожидаю указаний...",
          flush=True)
    while True:
        with Session(engine) as session:
            pending = snapshot(session)
        if pending:
            print("=== НОВЫЕ УКАЗАНИЯ ОТ МОДЕРАТОРА ===", flush=True)
            print(json.dumps({"count": len(pending), "threads": pending},
                             ensure_ascii=False, indent=2), flush=True)
            print("=== Обработайте через: python -m tools.agent_feedback show <id> ===",
                  flush=True)
            return 0
        if max_wait and (time.time() - started) > max_wait:
            print("[watch] Тайм-аут ожидания, новых указаний нет.", flush=True)
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
