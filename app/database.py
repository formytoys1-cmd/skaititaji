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


def _run_migrations_postgres() -> None:
    """Приводит прод-схему (Postgres) к head через Alembic, самовосстанавливаясь.

    Обрабатывает три состояния БД:
    - чистая БД → ``upgrade head`` создаёт всё с нуля;
    - легаси-БД (создана старым ``create_all``, без ``alembic_version``) →
      ``stamp`` начальной ревизии (она в точности отражает до-миграционную
      схему), затем ``upgrade head`` применяет только новые миграции;
    - уже версионированная БД → ``upgrade head``.

    Запускается при старте (единственный инстанс на Render). Идемпотентно.
    """
    from sqlalchemy import inspect

    from alembic import command
    from alembic.config import Config

    _INITIAL_REVISION = "a058bbc27f26"

    insp = inspect(engine)
    has_core = insp.has_table("organization")      # маркер легаси create_all-схемы
    has_version = insp.has_table("alembic_version")

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

    if has_core and not has_version:
        # Легаси-БД: схема уже соответствует начальной ревизии — фиксируем её,
        # чтобы upgrade применил только дельты (unique, audit_log, eIDAS).
        command.stamp(cfg, _INITIAL_REVISION)
    command.upgrade(cfg, "head")


def init_db() -> None:
    """Готовит схему БД.

    - Prod/Postgres: схемой управляют миграции Alembic. Применяются при старте
      самовосстанавливающимся мостом (``_run_migrations_postgres``), в т.ч. для
      легаси-БД, созданных старым ``create_all`` (см. docs/DEPLOY.md).
    - Dev/тесты (sqlite): используем ``create_all`` для мгновенного старта демо
      без миграций.
    """
    # Импортируем модели, чтобы они зарегистрировались в metadata
    import app.models  # noqa: F401

    if _is_sqlite:
        SQLModel.metadata.create_all(engine)
    else:
        _run_migrations_postgres()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
