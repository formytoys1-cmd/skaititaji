#!/usr/bin/env bash
# Авто-деплой платформы «Skaitītāji» на Google Cloud Run.
#
# Требования (разово):
#   1) Установлен gcloud CLI:   brew install --cask google-cloud-sdk
#   2) Выполнен вход:           gcloud auth login   (открывает браузер, Google-аккаунт)
#   3) Активна оплата у проекта (Cloud Run имеет бесплатный ярус, но нужен billing account)
#
# Запуск:
#   PROJECT_ID=<ваш-проект> ./tools/deploy_cloudrun.sh
#
# Скрипт соберёт контейнер из Dockerfile и задеплоит сервис (публичный URL).
set -e
cd "$(dirname "$0")/.."

: "${PROJECT_ID:?Задайте PROJECT_ID=<id проекта GCP>}"
REGION="${REGION:-europe-north1}"       # Финляндия — ближе к Латвии
SERVICE="${SERVICE:-skaititaji-demo}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "✗ gcloud не установлен. Установите: brew install --cask google-cloud-sdk"
  exit 1
fi

echo "→ Проект: $PROJECT_ID, регион: $REGION, сервис: $SERVICE"
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

echo "→ Деплой из исходников (Cloud Build соберёт Dockerfile)..."
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars "VISMA_MOCK=1,SECRET_KEY=$(python -c 'import secrets;print(secrets.token_hex(16))')"

echo "✓ Готово. URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)'
