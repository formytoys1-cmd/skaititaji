# Production-образ платформы «Skaitītāji».
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --retries 5 --timeout 120 -r requirements.txt

COPY . .

# Каталог для SQLite/логов (для демо; в проде используйте PostgreSQL через DATABASE_URL).
RUN mkdir -p data

# PaaS передаёт порт через $PORT; локально по умолчанию 8080.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
