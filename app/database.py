"""Инициализация БД и выдача сессий.

Поддерживает SQLite (демо/локально) и PostgreSQL (прод, постоянные данные).
Render выдаёт строку вида ``postgres://...`` — нормализуем в
``postgresql+psycopg://...`` для драйвера psycopg 3.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


def _normalize_db_url(url: str) -> str:
    # Render/Heroku дают postgres:// — SQLAlchemy требует явный драйвер.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_db_url(settings.database_url)
_is_sqlite = DATABASE_URL.startswith("sqlite")

# Гарантируем наличие каталога для SQLite-файла
if _is_sqlite and DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,   # переподключение после простоя (важно для Postgres)
)


def init_db() -> None:
    """Готовит схему БД.

    - Prod/Postgres: схемой управляют миграции Alembic (``alembic upgrade head``
      применяется на деплое, см. docs/DEPLOY.md). ``create_all`` здесь НЕ
      вызывается, чтобы не обходить версионирование схемы.
    - Dev/тесты (sqlite): используем ``create_all`` для мгновенного старта демо
      без миграций.
    """
    # Импортируем модели, чтобы они зарегистрировались в metadata
    import app.models  # noqa: F401

    if _is_sqlite:
        SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
