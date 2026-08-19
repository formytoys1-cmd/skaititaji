#!/usr/bin/env python
"""Удалённый клиент консоли обратной связи (боевой сервер).

Работает с защищённым API агента (`/agent/api/...`) — читает треды модератора,
скачивает вложения и отвечает с авторством «агент» на боевом сайте, где нет
прямого доступа к БД.

Конфигурация через окружение:
  SKAIT_BASE_URL   базовый URL сайта (по умолчанию https://skaititaji.onrender.com)
  AGENT_API_KEY    ключ агента (совпадает с переменной на сервере)

Использование (из корня проекта, с активным venv):
  python -m tools.agent_remote threads
  python -m tools.agent_remote show <id>
  python -m tools.agent_remote pull <att_id> [dest_path]
  python -m tools.agent_remote reply  <id> "текст"
  python -m tools.agent_remote review <id> "что сделано"
  python -m tools.agent_remote ask    <id> "уточняющий вопрос"
  python -m tools.agent_remote done   <id>

Все команды печатают JSON.
"""
from __future__ import annotations

import base64
import json
import os
import sys

import httpx

BASE_URL = os.getenv("SKAIT_BASE_URL", "https://skaititaji.onrender.com").rstrip("/")
API_KEY = os.getenv("AGENT_API_KEY", "")


def _client() -> httpx.Client:
    if not API_KEY:
        print(json.dumps({"error": "AGENT_API_KEY not set"}))
        raise SystemExit(2)
    return httpx.Client(
        base_url=BASE_URL,
        headers={"X-Agent-Key": API_KEY},
        timeout=60,
    )


def _print(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_threads(only_active: bool = False) -> None:
    with _client() as c:
        r = c.get("/agent/api/threads", params={"only_active": only_active})
        _print(r.json())


def cmd_show(tid: int) -> None:
    with _client() as c:
        r = c.get(f"/agent/api/threads/{tid}")
        _print(r.json())


def cmd_pull(att_id: int, dest: str | None) -> None:
    with _client() as c:
        r = c.get(f"/agent/api/attachment/{att_id}")
        if r.status_code != 200:
            _print({"error": r.status_code, "detail": r.text}); return
        payload = r.json()
        data = base64.b64decode(payload["base64"])
        dest = dest or os.path.join("data", "received_forms", payload["filename"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        _print({"ok": True, "saved": dest, "size": len(data)})


def _reply(tid: int, body: str, status: str | None = None) -> None:
    with _client() as c:
        r = c.post(
            f"/agent/api/threads/{tid}/reply",
            json={"body": body, "status": status or ""},
        )
        _print(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"status": r.status_code, "text": r.text})


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__); return 1
    cmd = argv[0]
    if cmd == "threads":
        cmd_threads(only_active="--active" in argv)
    elif cmd == "show" and len(argv) >= 2:
        cmd_show(int(argv[1]))
    elif cmd == "pull" and len(argv) >= 2:
        cmd_pull(int(argv[1]), argv[2] if len(argv) >= 3 else None)
    elif cmd == "reply" and len(argv) >= 3:
        _reply(int(argv[1]), argv[2])
    elif cmd == "review" and len(argv) >= 3:
        _reply(int(argv[1]), argv[2], "review")
    elif cmd == "ask" and len(argv) >= 3:
        _reply(int(argv[1]), argv[2], "ask")
    elif cmd == "done" and len(argv) >= 2:
        _reply(int(argv[1]), "Pabeigts.", "done")
    else:
        print(__doc__); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
