# Тестирование (каркас M1)

Каркас автотестов реализован по мандату аудитора качества
([docs/AUDIT_MANDATE_QA_AGENT.md](AUDIT_MANDATE_QA_AGENT.md), Часть 3). Закрывает
находку **QA-001** (полное отсутствие автотестов) — предусловие для всех
остальных находок.

## Быстрый старт

```bash
pip install -r requirements-dev.txt

# все тесты
pytest

# с покрытием ключевых модулей и гейтом 80%
pytest --cov=app.auth --cov=app.config --cov=app.services \
       --cov-report=term-missing --cov-fail-under=80

# линт
ruff check app tests
```

Прогон unit+integration+security локально — **< 5 c**.

## Структура

```
tests/
  conftest.py          # фикстуры: engine (изолированная SQLite), session, client, factory
  factories.py         # синтетические данные (без реальных перс. данных)
  unit/                # чистая логика: auth (хэш/verify), services (валидация/аномалии/§41)
  integration/         # роутеры через TestClient: smoke, поток входа/выхода/guard
  security/            # SEC-* находки (demo-login, boot-guard, tenant, csrf, rate-limit)
  contracts/           # VISMA-* на замоканных httpx-ответах
  e2e/                 # Playwright (подача показаний, PWA)
```

## Изоляция БД

Каждый тест получает **свежую in-memory SQLite** (`StaticPool`) — это даёт ту же
гарантию, что и откат транзакции: тесты не влияют друг на друга и **не трогают
реальную БД** (`data/skaititaji.db`). Фикстура `client` перенаправляет engine
приложения, сид и зависимость `get_session` на тестовую БД.

## Фикстуры (conftest.py)

| Фикстура | Назначение |
|----------|-----------|
| `engine` | изолированный in-memory engine на один тест |
| `session` | `Session` к тестовой БД (unit/service-тесты) |
| `app_on_test_db` | FastAPI-приложение, целиком на тестовом engine |
| `client` | `TestClient` (lifespan сидирует демо-данные в тестовую БД) |
| `factory` | фабрики синтетических сущностей (`tests/factories.py`) |

## Маркеры

`smoke`, `unit`, `integration`, `security`, `contracts`, `e2e`, `slow`.
Пример: `pytest -m security`.

## Покрытие

Гейт CI — **≥ 80 % по ключевым логическим модулям** (`app.auth`, `app.config`,
`app.services`). Роутеры/шаблоны покрываются интеграционными и e2e-тестами по мере
закрытия находок (M2+). Текущее покрытие ключевых модулей — **93 %**.

## CI

Workflow `.github/workflows/tests.yml` (Часть 4):
`lint (ruff) → pytest (unit+integration+security) → coverage gate 80%`.
Тот же pytest-гейт встроен в `automerge.yml` — правки форк-агента **не сольются
в main**, если тесты красные.

## Соглашения

- Персональные данные в тестах — **только синтетические** (см. `factories.py`).
- Каждая находка безопасности закрывается по циклу **Reproduce → Fix → Verify →
  Guard → Document** (падающий тест → фикс → зелёный тест-страховка).
- Mock-режим Visma остаётся дефолтом демо; реальные вызовы — только в отдельном
  контрактном/e2e-профиле.
