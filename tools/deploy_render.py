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

import os
import sys

import httpx


API = "https://api.render.com/v1"


def _api(method: str, path: str, key: str, payload: dict | None = None):
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": "skaititaji-deploy",
    }
    try:
        r = httpx.request(method, API + path, headers=headers, json=payload, timeout=60)
    except Exception as e:
        raise SystemExit(f"Сетевая ошибка: {e}")
    if r.status_code >= 400:
        raise SystemExit(f"Render API {r.status_code}: {r.text}")
    return r.json() if r.content else {}


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
