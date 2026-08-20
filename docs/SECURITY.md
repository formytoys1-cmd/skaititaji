# Безопасность (Security)

Документ описывает модель безопасности платформы «Skaitītāji» и статус находок
аудита ([docs/AUDIT_MANDATE_QA_AGENT.md](AUDIT_MANDATE_QA_AGENT.md)). Каждая
находка закрыта по циклу **Reproduce → Fix → Verify → Guard → Document** с
покрывающими тестами в `tests/security`, `tests/contracts`, `tests/compliance`.

## Базовая гигиена (сохранена)

- Заголовки безопасности + HSTS на HTTPS, COOP, X-Permitted-Cross-Domain
  ([app/main.py](../app/main.py)).
- Сессионная cookie: HttpOnly, SameSite=Lax, Secure в проде, max_age 8ч.
- Пароли: PBKDF2-SHA256, 120 000 итераций, сравнение `hmac.compare_digest`
  ([app/auth.py](../app/auth.py)).
- Agent API отключается при незаданном ключе (503).
- Ролевой доступ `require_role(...)`, мультиарендная модель на `Organization`.

## Статус находок

| ID | Severity | Статус | Что сделано | Тесты |
|----|----------|--------|-------------|-------|
| SEC-001 | 🔴 | ✅ Закрыто | `/demo-login` доступен только вне прода; в проде → 404. Флаг `ALLOW_DEMO_LOGIN` (в проде по умолчанию 0). | `security/test_demo_login.py` |
| SEC-002 | 🔴 | ✅ Закрыто | `DEBUG` по умолчанию 0; в dev секрет сессии генерируется; в проде дефолтный `SECRET_KEY` запрещён. | `security/test_config_secret.py` |
| SEC-003 | 🟠 | ✅ Закрыто | Секреты интеграций шифруются at-rest (`app/secrets_crypto.py`, HKDF+HMAC-CTR+MAC); чтение маскируется. | `security/test_integration_secrets.py` |
| SEC-004 | 🟠 | ✅ Закрыто | `validate_production_config()` — boot-guard: дефолтный секрет/DEBUG/sqlite/demo-login/ключ шифрования. | `security/test_boot_guard.py` |
| SEC-005 | 🟠 | ✅ Закрыто | CSRF-токен для мутирующих POST-форм (double-submit + подпись в сессии). | `security/test_csrf.py` |
| SEC-006 | 🟠 | ✅ Закрыто | Rate-limiting и анти-enumeration на `/login`, `/registreties`. | `security/test_auth_ratelimit.py` |
| SEC-007 | 🟡 | ✅ Закрыто | Ключ агента сравнивается `hmac.compare_digest` (constant-time). | `security/test_agent_key.py` |
| SEC-008 | 🟠 | ✅ Закрыто | Изоляция арендаторов: helper `get_owned_or_404`, матрица IDOR-тестов. | `security/test_tenant_isolation.py` |
| DATA-001 | 🟠 | ✅ Закрыто | PostgreSQL + Alembic-миграции; самовосстанавливающийся init (stamp легаси → upgrade). | `infra/test_migrations.py` |
| DATA-002 | 🟡 | ✅ Закрыто | Уникальность `(meter_id, period)` + защита от гонок/дублей; dedupe-safe миграция. | `unit/test_reading_integrity.py` |
| VISMA-001 | 🟠 | ✅ Закрыто | Контракт Visma Horizon верифицирован на замоканных httpx-ответах. | `contracts/test_visma_horizon_contract.py` |
| VISMA-002 | 🟠 | ✅ Закрыто | Ретраи с backoff, идемпотентность записи, устойчивость к сетевым сбоям. | `contracts/test_visma_horizon_resilience.py` |
| GDPR-001 | 🟠 | ✅ Закрыто | Экспорт и удаление/анонимизация персональных данных субъекта. | `compliance/test_gdpr.py` |
| OPS-001 | 🟡 | ✅ Закрыто | Неизменяемый журнал аудита действий с показаниями. | `compliance/test_audit.py` |
| AUTH-001 | 🔵→🟠 | ✅ Каркас | Абстракция провайдера eIDAS (Smart-ID/eParaksts), mock по умолчанию, маршруты входа. | `contracts/test_eidas_auth_contract.py`, `integration/test_eidas_flow.py` |

## Прод-конфигурация (обязательно)

Boot-guard (`validate_production_config`) требует в проде:

| Переменная | Требование |
|-----------|-----------|
| `SECRET_KEY` | задан, не равен дефолту |
| `DEBUG` | `0` |
| `DATABASE_URL` | не sqlite (PostgreSQL) |
| `ALLOW_DEMO_LOGIN` | `0` (гостевой вход отключён) |
| `SECRETS_ENCRYPTION_KEY` | задан (шифрование секретов интеграций) |

При нарушении приложение **не стартует** и печатает список проблем.

## Демо-режим

Локально/демо: `demo-login` включён, Visma и eIDAS в mock-режиме, секрет сессии
эфемерный. Это безопасно, т.к. прод определяется явными сигналами платформы
(Render/ENVIRONMENT), а не флагом DEBUG.
