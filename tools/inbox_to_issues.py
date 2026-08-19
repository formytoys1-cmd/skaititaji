#!/usr/bin/env python
"""Мост «инбокс → GitHub Issues».

Читает боевой инбокс через защищённый agent-API и создаёт GitHub Issue на
каждое сообщение модератора, требующее внимания (последнее слово в треде за
модератором, тред активен). Идемпотентно: в тело каждого Issue вшивается
маркер `inbox-thread-<tid>-msg-<msgid>`; повторный запуск не создаёт дублей.

Так сообщения из веб-консоли становятся задачами в GitHub, которые можно
назначить на GitHub Copilot coding agent (автономные PR) — полностью без
запущенной локальной сессии агента.

Окружение:
  SKAIT_BASE_URL   базовый URL (по умолчанию https://skaititaji.onrender.com)
  AGENT_API_KEY    ключ агента (репо-секрет)
  GH_TOKEN         токен для gh CLI (в Actions — secrets.GITHUB_TOKEN)
  DRY_RUN          "1" — только печать, без создания Issue (для локального теста)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import httpx

BASE_URL = os.getenv("SKAIT_BASE_URL", "https://skaititaji.onrender.com").rstrip("/")
API_KEY = os.getenv("AGENT_API_KEY", "")
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
LABEL = "inbox"
CLOSED = {"done", "rejected"}
MARKER_RE = re.compile(r"inbox-thread-(\d+)-msg-(\d+)")


def _headers() -> dict:
    return {"X-Agent-Key": API_KEY}


def fetch_awaiting() -> list[dict]:
    """Треды, где последнее слово за модератором и тред активен, с деталями."""
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        r = c.get("/agent/api/threads", headers=_headers())
        r.raise_for_status()
        awaiting = [
            t for t in r.json().get("threads", [])
            if t.get("last_author") == "moderator" and t.get("status") not in CLOSED
        ]
        details = []
        for t in awaiting:
            d = c.get(f"/agent/api/threads/{t['id']}", headers=_headers())
            d.raise_for_status()
            details.append(d.json())
        return details


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def ensure_label() -> None:
    subprocess.run(
        ["gh", "label", "create", LABEL, "--color", "0E8A16",
         "--description", "Ziņa no atgriezeniskās saites konsoles", "--force"],
        capture_output=True, text=True,
    )


def existing_markers() -> set[str]:
    """Маркеры уже созданных Issue (любого статуса) с меткой inbox."""
    res = gh("issue", "list", "--label", LABEL, "--state", "all",
             "--limit", "200", "--json", "body", check=False)
    if res.returncode != 0:
        return set()
    try:
        items = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        return set()
    found: set[str] = set()
    for it in items:
        for m in MARKER_RE.finditer(it.get("body") or ""):
            found.add(m.group(0))
    return found


def last_moderator_msg(detail: dict) -> dict | None:
    mods = [m for m in detail.get("messages", []) if m.get("author") == "moderator"]
    return mods[-1] if mods else None


def create_issue(detail: dict) -> str | None:
    thread = detail["thread"]
    tid = thread["id"]
    msg = last_moderator_msg(detail)
    if not msg:
        return None
    marker = f"inbox-thread-{tid}-msg-{msg['id']}"
    title = f"📨 Inbox #{tid}: {thread.get('title') or 'ziņa'}"[:120]
    atts = detail.get("attachments", [])
    att_lines = "\n".join(
        f"- {a['filename']} ({a.get('content_type') or '?'}, {a.get('size', 0)} B)"
        for a in atts
    ) or "—"
    body = (
        f"**Ziņa no moderatora** (konsole `/admin/inbox`, tēma #{tid}):\n\n"
        f"> {(msg.get('body') or '').strip().replace(chr(10), chr(10)+'> ')}\n\n"
        f"**Pielikumi:** \n{att_lines}\n\n"
        f"**Statuss:** {thread.get('status')} · **Prioritāte:** {thread.get('priority')}\n"
        f"**Konsole:** {BASE_URL}/admin/inbox/{tid}\n\n"
        f"<sub>Automātiski izveidots no atgriezeniskās saites. "
        f"Marķieris: {marker}</sub>\n"
        f"<!-- {marker} -->"
    )
    if DRY_RUN:
        print(f"[dry-run] создал бы Issue: {title}\n  marker={marker}")
        return marker
    ensure_label()
    res = gh("issue", "create", "--title", title, "--body", body,
             "--label", LABEL, check=False)
    if res.returncode != 0:
        print(f"[error] gh issue create: {res.stderr.strip()}", file=sys.stderr)
        return None
    print(f"[ok] Issue создан: {res.stdout.strip()}  ({marker})")
    return marker


def main() -> int:
    if not API_KEY:
        print("AGENT_API_KEY not set", file=sys.stderr)
        return 2
    try:
        details = fetch_awaiting()
    except Exception as e:
        print(f"[error] чтение инбокса не удалось: {e}", file=sys.stderr)
        return 1

    if not details:
        print("[inbox-to-issues] новых сообщений модератора нет.")
        return 0

    present = set() if DRY_RUN else existing_markers()
    created = 0
    for d in details:
        tid = d["thread"]["id"]
        msg = last_moderator_msg(d)
        if not msg:
            continue
        marker = f"inbox-thread-{tid}-msg-{msg['id']}"
        if marker in present:
            print(f"[skip] уже есть Issue для {marker}")
            continue
        if create_issue(d):
            created += 1
    print(f"[inbox-to-issues] создано Issue: {created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
