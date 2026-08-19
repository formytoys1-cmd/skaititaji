#!/usr/bin/env python
"""Находит свободный TCP-порт, начиная с заданного (по умолчанию 8000).

Печатает номер свободного порта в stdout. Используется скриптами запуска,
чтобы не падать при занятом порту.
"""
from __future__ import annotations

import socket
import sys


def is_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_free(start: int = 8000, limit: int = 100) -> int:
    for port in range(start, start + limit):
        if is_free(port):
            return port
    raise SystemExit(f"Свободный порт не найден в диапазоне {start}..{start+limit}")


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(find_free(start))
