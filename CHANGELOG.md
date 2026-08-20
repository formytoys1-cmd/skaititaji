# CHANGELOG

Значимые изменения проекта. Формат вдохновлён Keep a Changelog.

## [Unreleased] — аудит качества/безопасности (M1–M8)

Реализация мандата аудитора ([docs/AUDIT_MANDATE_QA_AGENT.md](docs/AUDIT_MANDATE_QA_AGENT.md)).
Все находки закрыты по циклу Reproduce → Fix → Verify → Guard → Document.

### Добавлено
- **Каркас тестирования (M1, QA-001):** `tests/` (unit/integration/security/
  contracts/compliance/infra/e2e), `conftest.py` (изолированная БД на тест,
  фабрики синтетики), CI `tests.yml` (ruff → pytest → gate покрытия 80%).
  Покрытие ключевых модулей ~94%.
- **PostgreSQL + Alembic (DATA-001):** версионирование схемы, самовосстанав-
  ливающийся init (для легаси-БД: `stamp` начальной ревизии → `upgrade head`).
- **Шифрование секретов интеграций at-rest (SEC-003):** `app/secrets_crypto.py`.
- **CSRF-защита (SEC-005), rate-limiting/анти-enumeration (SEC-006).**
- **Изоляция арендаторов (SEC-008):** helper `get_owned_or_404`, матрица IDOR.
- **Идемпотентность подачи (DATA-002):** уникальность `(meter_id, period)`,
  dedupe-safe миграция.
- **Контракты Visma Horizon (VISMA-001/002):** ретраи, backoff, идемпотентность.
- **GDPR-001:** экспорт и удаление/анонимизация персональных данных.
- **OPS-001:** неизменяемый журнал аудита действий с показаниями.
- **AUTH-001:** абстракция провайдера eIDAS (Smart-ID/eParaksts), mock по умолч.
- Документы: `docs/TESTING.md`, `docs/SECURITY.md`.

### Изменено (безопасные дефолты)
- `DEBUG` по умолчанию **выключен** (SEC-002).
- В dev секрет сессии генерируется автоматически; в проде дефолтный
  `SECRET_KEY` запрещён (SEC-002/SEC-004).
- `/demo-login` доступен только вне прода → 404 в проде (SEC-001).
- Сравнение ключа агента — `hmac.compare_digest` (SEC-007).
- Boot-guard `validate_production_config()` при старте в проде (SEC-004).

### Требования к прод-окружению
Заданы переменные: `SECRET_KEY`, `DEBUG=0`, `DATABASE_URL` (PostgreSQL),
`ALLOW_DEMO_LOGIN=0`, `SECRETS_ENCRYPTION_KEY`. См. [docs/SECURITY.md](docs/SECURITY.md).

### Примечание о деплое
Первый деплой на существующую боевую БД применяет миграции автоматически
(легаси-схема без `alembic_version` штампуется начальной ревизией, затем
накатываются дельты). Демо-вход в браузере в проде отключается (SEC-001);
доступ к консоли через agent-API сохраняется.
