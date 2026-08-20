#!/usr/bin/env python
"""PWA smoke-тест для CI: проверяет ключевые эндпоинты установки приложения.

Проверяет, что сайт остаётся устанавливаемым как мобильное приложение:
  - /manifest.webmanifest (валидный JSON, standalone, есть иконки + maskable)
  - /sw.js (service worker, Service-Worker-Allowed: /)
  - /offline (офлайн-страница)
  - иконки 192/512 и apple-touch-icon доступны
  - в HTML главной есть link rel=manifest, theme-color и регистрация SW

Код возврата 0 — всё ок; 1 — есть провал (CI падает).

Использование: python tools/audit/pwa_check.py [BASE_URL]
"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def get(path: str) -> tuple[int, object, bytes]:
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "pwa-check"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.headers, r.read()  # r.headers — регистронезависим
    except Exception as e:  # noqa: BLE001
        return 0, None, str(e).encode()


def main() -> int:
    fails: list[str] = []

    # manifest
    st, hdrs, body = get("/manifest.webmanifest")
    if st != 200:
        fails.append(f"manifest status {st}")
    else:
        try:
            m = json.loads(body)
            if m.get("display") != "standalone":
                fails.append("manifest.display != standalone")
            icons = m.get("icons", [])
            if not any(i.get("sizes") == "512x512" for i in icons):
                fails.append("нет иконки 512x512")
            if not any(i.get("purpose") == "maskable" for i in icons):
                fails.append("нет maskable-иконки")
        except json.JSONDecodeError:
            fails.append("manifest не валидный JSON")

    # service worker
    st, hdrs, _ = get("/sw.js")
    if st != 200:
        fails.append(f"sw.js status {st}")
    elif (hdrs.get("Service-Worker-Allowed") if hdrs else None) != "/":
        fails.append("нет заголовка Service-Worker-Allowed: /")

    # offline page
    st, _, _ = get("/offline")
    if st != 200:
        fails.append(f"/offline status {st}")

    # иконки
    for p in ("/static/icons/icon-192.png", "/static/icons/icon-512.png",
              "/static/icons/apple-touch-icon.png"):
        st, _, _ = get(p)
        if st != 200:
            fails.append(f"{p} status {st}")

    # HTML главной
    st, _, body = get("/")
    html = body.decode("utf-8", "ignore")
    for needle, label in [
        ('rel="manifest"', "link rel=manifest"),
        ('name="theme-color"', "theme-color"),
        ("serviceWorker.register('/sw.js')", "регистрация SW"),
    ]:
        if needle not in html:
            fails.append(f"в HTML нет: {label}")

    if fails:
        print("❌ PWA smoke FAILED:")
        for f in fails:
            print("  -", f)
        return 1
    print("✅ PWA smoke passed (manifest, SW, offline, icons, head-теги).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
