#!/usr/bin/env python
"""Автодеплой в Render: создаёт бесплатный Web Service из ПУБЛИЧНОГО git-репо.

Для публичного репозитория Render API не требует OAuth-подключения GitHub —
достаточно ключа API. Токен читается только из окружения RENDER_API_KEY и не
сохраняется в файлы/логи.

Использование:
    RENDER_API_KEY=<key> python -m tools.deploy_render <public_repo_url> [service_name]

Печатает URL сервиса Render (публичный адрес сайта).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request


API = "https://api.render.com/v1"


def _api(method: str, path: str, key: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "skaititaji-deploy")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Render API {e.code}: {e.read().decode()}")


def main(argv: list[str]) -> int:
    key = os.getenv("RENDER_API_KEY", "").strip()
    if not key or len(argv) < 1:
        print(__doc__); return 1
    repo_url = argv[0].rstrip("/")
    name = argv[1] if len(argv) > 1 else "skaititaji-demo"

    # Владелец (workspace)
    owners = _api("GET", "/owners", key)
    owner_id = owners[0]["owner"]["id"] if owners else None
    print(f"→ Render workspace owner: {owner_id}")

    payload = {
        "type": "web_service",
        "name": name,
        "ownerId": owner_id,
        "repo": repo_url,
        "autoDeploy": "yes",
        "branch": "main",
        "serviceDetails": {
            "env": "python",
            "plan": "free",
            "region": "frankfurt",
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
            },
        },
        "envVars": [
            {"key": "VISMA_MOCK", "value": "1"},
            {"key": "PYTHON_VERSION", "value": "3.12.6"},
        ],
    }
    print(f"→ Создаю Web Service '{name}' из {repo_url} ...")
    res = _api("POST", "/services", key, payload)
    svc = res.get("service", res)
    sid = svc.get("id")
    url = svc.get("serviceDetails", {}).get("url") or svc.get("dashboardUrl")
    print(f"✓ Сервис создан: id={sid}")
    print(f"SERVICE_URL={url}")
    print(f"DASHBOARD={svc.get('dashboardUrl')}")
    print("→ Сборка и деплой идут автоматически (несколько минут).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
