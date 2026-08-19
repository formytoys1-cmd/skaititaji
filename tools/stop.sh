#!/usr/bin/env bash
# Останавливает сервер, запущенный через tools/start.sh (по data/server.pid).
set -e
cd "$(dirname "$0")/.."

if [ -f data/server.pid ]; then
  PID="$(cat data/server.pid)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "✓ Сервер остановлен (PID $PID)"
  else
    echo "Сервер не запущен (PID $PID не активен)"
  fi
  rm -f data/server.pid
else
  echo "PID-файл не найден (data/server.pid). Сервер, вероятно, не запущен."
fi
