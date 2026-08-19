#!/usr/bin/env python
"""Live-сторож консоли обратной связи: «будит» агента при новом сообщении.

Опрашивает боевой инбокс через защищённый agent-API (/agent/api/threads) и
завершается (exit 0), как только появляется тред, где последнее слово за
модератором и тред ещё активен (т.е. агент должен ответить/сделать). Печатает
полное содержимое таких тредов (сообщения + вложения) в JSON.

Механика «пробуждения»: агент запускает этот скрипт как фоновую команду и
завершает свой ход. Когда пользователь пишет в /admin/inbox, скрипт находит
это и завершается — среда уведомляет агента о завершении фоновой команды, что
запускает новый ход. Агент обрабатывает указание, отвечает через agent-API и
снова запускает сторожа. Так получается интерактивный цикл.

Окружение:
  SKAIT_BASE_URL    базовый URL (по умолчанию https://skaititaji.onrender.com)
  AGENT_API_KEY     ключ агента (как на сервере)
  FB_POLL_INTERVAL  интервал опроса, сек (по умолчанию 20)
  FB_MAX_WAIT       макс. ожидание, сек (0 = бесконечно; по умолчанию 0)
  FB_HEARTBEAT      печатать строку «жив» каждые N сек (0 = выкл; по умолч. 300)
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

BASE_URL = os.getenv("SKAIT_BASE_URL", "https://skaititaji.onrender.com").rstrip("/")
API_KEY = os.getenv("AGENT_API_KEY", "")
POLL = float(os.getenv("FB_POLL_INTERVAL", "20"))
MAX_WAIT = float(os.getenv("FB_MAX_WAIT", "0"))
HEARTBEAT = float(os.getenv("FB_HEARTBEAT", "300"))

# Статусы, в которых тред НЕ ждёт агента (закрыт/отклонён).
CLOSED = {"done", "rejected"}


def _headers() -> dict:
    return {"X-Agent-Key": API_KEY}


def awaiting_threads(client: httpx.Client) -> list[dict]:
    """Треды, где последнее слово за модератором и тред активен."""
    r = client.get("/agent/api/threads", headers=_headers(), timeout=30)
    r.raise_for_status()
    out = []
    for t in r.json().get("threads", []):
        if t.get("last_author") == "moderator" and t.get("status") not in CLOSED:
            out.append(t)
    return out


def thread_detail(client: httpx.Client, tid: int) -> dict:
    r = client.get(f"/agent/api/threads/{tid}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def main() -> int:
    if not API_KEY:
        print(json.dumps({"error": "AGENT_API_KEY not set"}))
        return 2

    started = time.time()
    last_beat = 0.0
    print(f"[watch-live] Слежу за {BASE_URL}/admin/inbox (каждые {POLL:.0f}s). "
          f"Ожидаю сообщений модератора...", flush=True)

    with httpx.Client(base_url=BASE_URL) as client:
        while True:
            try:
                pending = awaiting_threads(client)
            except Exception as e:  # сеть/холодный старт Render — не падаем
                print(f"[watch-live] опрос не удался: {e}", flush=True)
                pending = []

            if pending:
                details = []
                for t in pending:
                    try:
                        details.append(thread_detail(client, t["id"]))
                    except Exception as e:
                        details.append({"thread": t, "error": str(e)})
                print("=== НОВОЕ СООБЩЕНИЕ МОДЕРАТОРА (нужен ответ агента) ===",
                      flush=True)
                print(json.dumps({"count": len(details), "threads": details},
                                 ensure_ascii=False, indent=2), flush=True)
                print("=== Обработайте и ответьте: "
                      "python -m tools.agent_remote reply <id> \"...\" ===",
                      flush=True)
                return 0

            now = time.time()
            if HEARTBEAT and (now - last_beat) >= HEARTBEAT:
                print(f"[watch-live] жив, {int(now - started)}s без новых сообщений",
                      flush=True)
                last_beat = now
            if MAX_WAIT and (now - started) > MAX_WAIT:
                print("[watch-live] тайм-аут, новых сообщений нет.", flush=True)
                return 0
            time.sleep(POLL)


if __name__ == "__main__":
    raise SystemExit(main())
