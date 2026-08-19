#!/usr/bin/env python
"""Проверка HTTP security-заголовков (OWASP Secure Headers) на живом/локальном URL.

Использование:
    python tools/audit/check_headers.py [URL]
    (по умолчанию http://127.0.0.1:8000)

Завершается с кодом 1, если отсутствуют обязательные заголовки — «ворота» для CI.
Использует httpx (встроенные TLS-сертификаты).
"""
from __future__ import annotations

import sys

import httpx

REQUIRED = {
    "content-security-policy": "CSP",
    "x-content-type-options": "nosniff",
    "x-frame-options": "clickjacking",
    "referrer-policy": "referrer",
    "permissions-policy": "permissions",
}
RECOMMENDED = {
    "strict-transport-security": "HSTS (только HTTPS)",
    "cross-origin-opener-policy": "COOP",
}


def main(url: str) -> int:
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True)
    except Exception as e:
        print(f"✗ Не удалось получить {url}: {e}")
        return 1

    headers = {k.lower(): v for k, v in r.headers.items()}
    missing = []
    print(f"Проверка заголовков: {url}\n")
    for h, desc in REQUIRED.items():
        ok = h in headers
        print(f"  {'✓' if ok else '✗'} {h:32} {desc}")
        if not ok:
            missing.append(h)
    for h, desc in RECOMMENDED.items():
        ok = h in headers
        mark = "✓" if ok else "•"
        print(f"  {mark} {h:32} {desc} (recommended)")

    # HSTS обязателен только на HTTPS
    if url.startswith("https://") and "strict-transport-security" not in headers:
        missing.append("strict-transport-security")

    print()
    if missing:
        print(f"❌ Отсутствуют обязательные заголовки: {', '.join(missing)}")
        return 1
    print("✅ Все обязательные security-заголовки присутствуют.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    raise SystemExit(main(target))
