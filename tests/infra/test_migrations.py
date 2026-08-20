"""DATA-001: миграции Alembic применяются на чистой БД.

Гарантирует, что схема управляется миграциями (а не только create_all) и что
``alembic upgrade head`` поднимает все таблицы моделей на пустой базе.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.slow
def test_migrations_apply_clean(tmp_path):
    """`alembic upgrade head` на пустой БД создаёт все таблицы моделей."""
    import app.models  # noqa: F401  — регистрируем модели в metadata
    from alembic import command
    from alembic.config import Config

    db_url = f"sqlite:///{tmp_path / 'migrate.db'}"

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")

    engine = create_engine(db_url)
    try:
        actual = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    expected = set(SQLModel.metadata.tables.keys())
    missing = expected - actual
    assert not missing, f"миграции не создали таблицы: {sorted(missing)}"
