"""Окружение Alembic (DATA-001).

- Метаданные берутся из моделей приложения (SQLModel.metadata), чтобы
  автогенерация видела актуальную схему.
- URL БД читается из окружения (DATABASE_URL) с той же нормализацией, что и в
  рантайме (``postgres://`` → ``postgresql+psycopg://``), либо из
  ``sqlalchemy.url`` конфигурации (для тестов/оффлайна).
"""
from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  — регистрируем все таблицы в metadata
from alembic import context
from app.config import settings
from app.database import _normalize_db_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _database_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        url = _normalize_db_url(settings.database_url)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
