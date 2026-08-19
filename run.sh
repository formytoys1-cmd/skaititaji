#!/usr/bin/env bash
# Быстрый запуск демо-платформы «Skaitītāji» (foreground, с авто-выбором порта).
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "→ Создаю виртуальное окружение..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "→ Устанавливаю зависимости..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "→ Готовлю демо-данные..."
python -m app.seed

HOST="${HOST:-127.0.0.1}"
START_PORT="${PORT:-8000}"
PORT="$(python -m tools.find_port "$START_PORT")"
if [ "$PORT" != "$START_PORT" ]; then
  echo "⚠ Порт $START_PORT занят — использую свободный $PORT"
fi
echo "→ Запускаю сервер на http://$HOST:$PORT  (демо: /demo, консоль: /admin/inbox)"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
