#!/usr/bin/env bash
# Запуск сервера с автоматическим выбором свободного порта (без конфликтов).
# Порт и PID сохраняются в data/ для последующей остановки.
set -e
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet -r requirements.txt >/dev/null 2>&1 || true

mkdir -p data
HOST="${HOST:-127.0.0.1}"
START_PORT="${PORT:-8000}"

# Если старый инстанс запущен по нашему PID-файлу — остановим его раньше выбора порта.
if [ -f data/server.pid ]; then
  OLD_PID="$(cat data/server.pid 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "→ Останавливаю прежний сервер (PID $OLD_PID)"
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
fi

PORT="$(python -m tools.find_port "$START_PORT")"

python -m app.seed >/dev/null 2>&1 || true

echo "$PORT" > data/server.port
echo "→ Запускаю сервер на http://$HOST:$PORT  (демо: /demo, консоль: /admin/inbox)"
nohup uvicorn app.main:app --host "$HOST" --port "$PORT" > data/server.log 2>&1 &
echo $! > data/server.pid
sleep 2
if kill -0 "$(cat data/server.pid)" 2>/dev/null; then
  echo "✓ Сервер работает, PID $(cat data/server.pid), порт $PORT"
else
  echo "✗ Сервер не запустился, смотрите data/server.log"; exit 1
fi
