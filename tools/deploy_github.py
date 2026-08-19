#!/usr/bin/env python
"""Автодеплой в GitHub: создаёт репозиторий и заливает код токеном.

Токен НЕ сохраняется в файлы/логи — читается только из окружения GITHUB_TOKEN.
После деплоя токен можно (и нужно) сразу отозвать.

Использование:
    GITHUB_TOKEN=<token> python -m tools.deploy_github [repo_name]

Печатает URL созданного публичного репозитория (для Render).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import httpx


def _api(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "skaititaji-deploy",
    }
    try:
        r = httpx.request(method, url, headers=headers, json=payload, timeout=30)
    except Exception as e:
        raise SystemExit(f"Сетевая ошибка: {e}")
    if r.status_code >= 400:
        raise SystemExit(f"GitHub API {r.status_code}: {r.text}")
    return r.json() if r.content else {}


def main(argv: list[str]) -> int:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        print("✗ Задайте GITHUB_TOKEN=<token>"); return 1
    repo = (argv[0] if argv else "skaititaji").strip()

    # Кто владелец токена
    me = _api("GET", "https://api.github.com/user", token)
    login = me["login"]
    print(f"→ GitHub пользователь: {login}")

    # Существует ли репозиторий
    exists = False
    try:
        _api("GET", f"https://api.github.com/repos/{login}/{repo}", token)
        exists = True
        print(f"→ Репозиторий уже существует: {login}/{repo}")
    except SystemExit:
        pass

    if not exists:
        print(f"→ Создаю публичный репозиторий {login}/{repo} ...")
        _api("POST", "https://api.github.com/user/repos", token, {
            "name": repo,
            "description": "Skaititaji — платформа подачи показаний счётчиков",
            "private": False,
            "auto_init": False,
        })

    remote = f"https://{login}:{token}@github.com/{login}/{repo}.git"
    public_url = f"https://github.com/{login}/{repo}"

    # Пуш текущего HEAD (git remote с токеном НЕ печатаем)
    subprocess.run(["git", "remote", "remove", "origin"],
                   check=False, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", remote], check=True)
    print("→ Заливаю код (git push) ...")
    r = subprocess.run(["git", "push", "-u", "origin", "main", "--force"],
                       capture_output=True, text=True)
    # Убираем токен из remote, чтобы он не оставался в конфиге
    subprocess.run(["git", "remote", "set-url", "origin", public_url + ".git"],
                   check=False, capture_output=True)
    if r.returncode != 0:
        print(r.stderr); raise SystemExit("✗ git push не удался")

    print("✓ Готово.")
    print(f"PUBLIC_REPO_URL={public_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
