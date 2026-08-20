"""Общие фикстуры для тестов (см. docs/AUDIT_MANDATE_QA_AGENT.md, Часть 3.2).

Ключевые принципы:
- Каждый тест получает ИЗОЛИРОВАННУЮ in-memory SQLite-БД (StaticPool) — это даёт
  ту же гарантию, что и откат транзакции: тесты не влияют друг на друга и не
  трогают реальную БД проекта (data/skaititaji.db).
- `client` направляет приложение (engine, сид, зависимости) на тестовый engine.
- Все персональные данные — синтетические (tests/factories.py).
"""
from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture()
def engine():
    """Изолированный in-memory SQLite для одного теста (общий для всех соединений)."""
    import app.models  # noqa: F401  — регистрируем таблицы в metadata
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    try:
        yield eng
    finally:
        SQLModel.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def session(engine):
    """Сессия к изолированной тестовой БД (для unit/service-тестов и фабрик)."""
    with Session(engine) as s:
        yield s


@pytest.fixture()
def app_on_test_db(engine, monkeypatch):
    """FastAPI-приложение, целиком перенаправленное на тестовый engine.

    Патчим все места, где используется боевой engine (database/seed/main),
    чтобы старт приложения (init_db/seed) и запросы шли в тестовую БД.
    """
    monkeypatch.setattr("app.database.engine", engine, raising=False)
    monkeypatch.setattr("app.seed.engine", engine, raising=False)
    # Чтобы кастомный 404-обработчик тоже смотрел в тестовую БД:
    import app.main as main_module
    monkeypatch.setattr(main_module, "_engine", engine, raising=False)

    from app.database import get_session
    from app.main import app

    def _get_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture()
def client(app_on_test_db):
    """TestClient с прогоном lifespan (сид демо-данных в тестовую БД).

    Демо-данные удобны для smoke/интеграции; для строгой изоляции тестов
    используйте фабрики из tests/factories.py на фикстуре `session`.
    """
    from fastapi.testclient import TestClient

    with TestClient(app_on_test_db) as c:
        yield c


@pytest.fixture()
def factory(session):
    """Доступ к фабрикам синтетических данных, привязанным к тестовой сессии."""
    from tests import factories

    return factories.Factory(session)


def csrf_token(client) -> str:
    """Возвращает актуальный CSRF-токен для сессии клиента (SEC-005).

    Токен привязан к сессии и одинаков для всех форм, поэтому достаточно
    один раз получить любую страницу с формой (например, /login).
    """
    import re

    html = client.get("/login").text
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert m, "CSRF hidden field not found"
    return m.group(1)


@pytest.fixture()
def csrf(client):
    """Фикстура-помощник: CSRF-токен текущей сессии клиента."""
    return csrf_token(client)
