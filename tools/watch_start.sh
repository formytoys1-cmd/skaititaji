#!/usr/bin/env bash
# Запуск live-сторожа консоли обратной связи.
# Читает ключ агента из data/agent_api_key.txt и следит за боевым инбоксом.
# Как только появляется сообщение модератора — печатает его и завершается
# (это «будит» агента через уведомление о завершении фоновой команды).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [ -z "${AGENT_API_KEY:-}" ] && [ -f data/agent_api_key.txt ]; then
  AGENT_API_KEY="$(cat data/agent_api_key.txt)"
  export AGENT_API_KEY
fi

export SKAIT_BASE_URL="${SKAIT_BASE_URL:-https://skaititaji.onrender.com}"
export FB_POLL_INTERVAL="${FB_POLL_INTERVAL:-20}"
export FB_MAX_WAIT="${FB_MAX_WAIT:-0}"

exec python -m tools.agent_watch_live
