#!/usr/bin/env python3
"""Монитор актуальности справки и работоспособности QR/демо.

Проверяет то, что обещано в docs/QUICK_REFERENCE.md и в справочном чате:
  1. Сайт жив: GET /api/health == 200 и status == ok.
  2. QR-коды работают: /qr/site.svg, /qr/app.svg, /qr/help.svg == 200, валидный SVG.
  3. Страница «Поделиться» /koplietosana == 200.
  4. Демо-доступ корректен: /demo ссылается на /login?demo=<role>, НЕ на /demo-login.
  5. /demo-login отключён в проде (404) — SEC-001.
  6. Реальный демо-вход работает: resident/manager/admin -> 303 в свой кабинет.
  7. Ссылки из справки резолвятся: /, /login, /palidziba, /koplietosana.

Возвращает ненулевой код при любой поломке (для алерта в CI/по расписанию).

Использование:
    python tools/reference_check.py                # прод по умолчанию
    BASE=http://127.0.0.1:8000 python tools/reference_check.py
"""
from __future__ import annotations

import os
import re
import sys

import httpx

BASE = os.getenv("BASE", "https://skaititaji.onrender.com").rstrip("/")
TIMEOUT = float(os.getenv("TIMEOUT", "30"))

# Ожидаемые маршруты кабинетов после входа демо-ролями.
DEMO_ACCOUNTS = {
    "resident@demo.lv": "/dzivoklis",
    "manager@demo.lv": "/parvalde",
    "admin@demo.lv": "/admin",
}
DEMO_PASSWORD = "demo1234"

failures: list[str] = []
oks: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (oks if ok else failures).append(f"{name}{(' — ' + detail) if detail else ''}")
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}", flush=True)


def get(client: httpx.Client, path: str, **kw):
    try:
        return client.get(path, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=TIMEOUT, follow_redirects=False) as c:
        # 1. health
        r = get(c, "/api/health")
        ok = not isinstance(r, Exception) and r.status_code == 200 and \
            r.json().get("status") == "ok"
        check("health /api/health", ok,
              "" if ok else f"{getattr(r, 'status_code', r)}")

        # 2. QR endpoints
        for name in ("site", "app", "help"):
            r = get(c, f"/qr/{name}.svg")
            ok = not isinstance(r, Exception) and r.status_code == 200 and \
                "svg" in r.headers.get("content-type", "") and "<svg" in r.text[:200]
            check(f"QR /qr/{name}.svg", ok,
                  "" if ok else f"{getattr(r, 'status_code', r)}")

        # 3. share page
        r = get(c, "/koplietosana")
        check("share /koplietosana", not isinstance(r, Exception) and r.status_code == 200,
              "" if not isinstance(r, Exception) else str(r))

        # 4. demo page links to /login?demo=, not /demo-login
        r = get(c, "/demo")
        if isinstance(r, Exception) or r.status_code != 200:
            check("demo page /demo", False, f"{getattr(r, 'status_code', r)}")
        else:
            body = r.text
            has_bypass = "/demo-login" in body
            has_prefill = all(f"/login?demo={role}" in body
                              for role in ("resident", "manager", "admin"))
            check("demo /demo links to /login?demo=<role>", has_prefill and not has_bypass,
                  "найден /demo-login (в проде это 404!)" if has_bypass
                  else ("нет части ссылок /login?demo=" if not has_prefill else ""))

        # 5. /demo-login disabled in prod (404). На localhost/dev может быть 303 — не валим.
        r = get(c, "/demo-login?role=resident")
        code = getattr(r, "status_code", None)
        if BASE.startswith("https://skaititaji.onrender.com"):
            check("SEC-001 /demo-login == 404 (prod)", code == 404, f"got {code}")
        else:
            check("SEC-001 /demo-login (dev, инфо)", True, f"got {code}")

        # 7. reference links resolve
        for path in ("/", "/login", "/palidziba"):
            r = get(c, path)
            check(f"link {path}", not isinstance(r, Exception) and r.status_code == 200,
                  "" if not isinstance(r, Exception) else str(r))

    # 6. real demo login per role (fresh session + CSRF each)
    for email, home in DEMO_ACCOUNTS.items():
        try:
            with httpx.Client(base_url=BASE, timeout=TIMEOUT,
                              follow_redirects=False) as c:
                page = c.get("/login")
                m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text)
                data = {"email": email, "password": DEMO_PASSWORD}
                if m:
                    data["csrf_token"] = m.group(1)
                rr = c.post("/login", data=data)
                ok = rr.status_code in (302, 303) and rr.headers.get("location") == home
                check(f"demo login {email}", ok,
                      "" if ok else f"{rr.status_code} -> {rr.headers.get('location','')}")
        except Exception as e:  # noqa: BLE001
            check(f"demo login {email}", False, str(e))

    print(f"\nИтог: {len(oks)} OK, {len(failures)} FAIL")
    if failures:
        print("ПОЛОМКИ:")
        for f in failures:
            print("  -", f)
        return 1
    print("Справка актуальна, QR и демо работают.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
