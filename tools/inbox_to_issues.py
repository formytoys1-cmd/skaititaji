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

# Авто-назначение созданных Issue на облачный GitHub Copilot coding agent.
# Включается автоматически, КОГДА агент доступен на репо (фича включена в
# настройках Copilot). Если бот недоступен — тихо пропускаем, воркфлоу работает
# как обычно. Отключить принудительно: ASSIGN_COPILOT=0.
REPO = os.getenv("GITHUB_REPOSITORY", "formytoys1-cmd/skaititaji")
ASSIGN_COPILOT = os.getenv("ASSIGN_COPILOT", "1") == "1"
# Возможные логины бота coding agent в suggestedActors.
_COPILOT_LOGINS = {"copilot-swe-agent", "Copilot", "copilot"}
_copilot_actor_id: str | None = None
_copilot_checked = False


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


def _graphql(query: str) -> dict | None:
    res = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        return None
    try:
        return json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        return None


def copilot_actor_id() -> str | None:
    """ID бота Copilot coding agent, если он назначаемый на этом репо (иначе None).

    Кэшируется на процесс. Это же и проверка «включена ли фича»: пока агент не
    активирован в настройках Copilot, бот не появляется в suggestedActors.
    """
    global _copilot_actor_id, _copilot_checked
    if _copilot_checked:
        return _copilot_actor_id
    _copilot_checked = True
    try:
        owner, name = REPO.split("/", 1)
    except ValueError:
        return None
    q = (
        f'query {{ repository(owner:"{owner}", name:"{name}") {{ '
        f'suggestedActors(capabilities:[CAN_BE_ASSIGNED], first:50) {{ '
        f'nodes {{ login __typename ... on Bot {{ id }} }} }} }} }}'
    )
    data = _graphql(q)
    if not data:
        return None
    nodes = (
        data.get("data", {}).get("repository", {})
        .get("suggestedActors", {}).get("nodes", []) or []
    )
    for n in nodes:
        if n.get("login") in _COPILOT_LOGINS and n.get("id"):
            _copilot_actor_id = n["id"]
            break
    return _copilot_actor_id


def _issue_node_id(number: int) -> str | None:
    owner, name = REPO.split("/", 1)
    q = (
        f'query {{ repository(owner:"{owner}", name:"{name}") {{ '
        f'issue(number:{number}) {{ id }} }} }}'
    )
    data = _graphql(q)
    if not data:
        return None
    return data.get("data", {}).get("repository", {}).get("issue", {}).get("id")


def assign_to_copilot(issue_url: str) -> bool:
    """Назначает Issue на Copilot coding agent. Возвращает True при успехе.

    Безопасно: если агент недоступен или что-то пошло не так — возвращает False,
    не роняя основной поток создания Issue.
    """
    actor_id = copilot_actor_id()
    if not actor_id:
        return False
    m = re.search(r"/issues/(\d+)", issue_url or "")
    if not m:
        return False
    node_id = _issue_node_id(int(m.group(1)))
    if not node_id:
        return False
    mutation = (
        f'mutation {{ replaceActorsForAssignable(input:{{'
        f'assignableId:"{node_id}", actorIds:["{actor_id}"]}}) {{ '
        f'assignable {{ ... on Issue {{ number }} }} }} }}'
    )
    data = _graphql(mutation)
    return bool(data and "errors" not in data)


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
    issue_url = res.stdout.strip()
    print(f"[ok] Issue создан: {issue_url}  ({marker})")
    if ASSIGN_COPILOT:
        if assign_to_copilot(issue_url):
            print(f"[ok] назначен на Copilot coding agent: {issue_url}")
        else:
            print("[info] Copilot coding agent недоступен — Issue без авто-назначения "
                  "(включите фичу в настройках Copilot, тогда назначится само).")
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
