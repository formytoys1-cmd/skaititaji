#!/usr/bin/env python
"""Мост управления из консоли обратной связи → действия в GitHub.

Опрашивает боевой инбокс через agent-API и по «командам» модератора запускает
действия в GitHub. Сейчас поддерживается автомердж форк-ветки в main.

Как пользователь инициирует мердж из консоли:
  - создать сообщение/тред, содержащее команду в квадратных скобках:
      [merge] либо [merge agent/console]
  - скрипт находит такую свежую команду, запускает workflow `automerge`
    (через repository_dispatch) и отвечает в тред от имени агента.

Идемпотентность: в тред пишется отметка «принято в работу: merge <sha_marker>»,
повторный запуск ту же команду не дублирует.

Запускается по расписанию GitHub Actions (console-control.yml) и/или локально.

Окружение:
  SKAIT_BASE_URL   базовый URL (по умолчанию https://skaititaji.onrender.com)
  AGENT_API_KEY    ключ агента
  GH_TOKEN         токен с правами actions:write (dispatch workflow)
"""
from __future__ import annotations

import os
import re
import sys

import httpx

BASE_URL = os.getenv("SKAIT_BASE_URL", "https://skaititaji.onrender.com").rstrip("/")
API_KEY = os.getenv("AGENT_API_KEY", "")
GH_TOKEN = os.getenv("GH_TOKEN", "")
REPO = "formytoys1-cmd/skaititaji"

MERGE_RE = re.compile(r"\[merge(?:\s+([\w./-]+))?\]", re.IGNORECASE)
ACCEPT_MARK = "⚙️ Команда принята: merge"


def _h() -> dict:
    return {"X-Agent-Key": API_KEY}


def _dispatch_automerge(branch: str) -> tuple[bool, str]:
    """Запускает workflow automerge через workflow_dispatch API."""
    if not GH_TOKEN:
        return False, "GH_TOKEN не задан"
    r = httpx.post(
        f"https://api.github.com/repos/{REPO}/actions/workflows/automerge.yml/dispatches",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"ref": "main", "inputs": {"branch": branch}},
        timeout=30,
    )
    return (r.status_code == 204), f"HTTP {r.status_code}"


def main() -> int:
    if not API_KEY:
        print("AGENT_API_KEY не задан", file=sys.stderr)
        return 2

    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        threads = c.get("/agent/api/threads", headers=_h()).json().get("threads", [])
        handled = 0
        for t in threads:
            tid = t["id"]
            detail = c.get(f"/agent/api/threads/{tid}", headers=_h()).json()
            msgs = detail.get("messages", [])
            if not msgs:
                continue
            # ищем последнюю команду модератора
            last = msgs[-1]
            if last.get("author") != "moderator":
                continue
            m = MERGE_RE.search(last.get("body") or "")
            if not m:
                continue
            # уже приняли эту команду? (есть отметка агента после этого сообщения)
            already = any(
                x.get("author") == "agent" and ACCEPT_MARK in (x.get("body") or "")
                and x["id"] > last["id"]
                for x in msgs
            )
            if already:
                continue

            branch = m.group(1) or "agent/console"
            ok, info = _dispatch_automerge(branch)
            reply = (
                f"{ACCEPT_MARK} `{branch}` → main.\n"
                + ("Запущен CI-мердж с проверками (a11y, PWA). Результат появится "
                   "после прохождения гейтов." if ok
                   else f"Не удалось запустить мердж: {info}.")
            )
            c.post(f"/agent/api/threads/{tid}/reply", headers=_h(),
                   json={"body": reply, "status": "progress"})
            print(f"thread #{tid}: merge {branch} dispatch={ok} ({info})")
            handled += 1

        print(f"console-control: обработано команд merge: {handled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
