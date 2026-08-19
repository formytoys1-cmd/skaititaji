# Концепция контроля качества, доступности и соответствия стандартам

Этот документ описывает **как** платформа «Skaitītāji» держит качество на высоком
уровне и **автоматически** это контролирует, а также как отслеживаются новые
версии стандартов.

## 1. Каким стандартам соответствуем

| Область | Стандарт / регламент | Как обеспечиваем |
|---|---|---|
| **Доступность** | WCAG 2.2 уровень **AA**; ЕС Директива 2016/2102 (веб-доступность) | axe-core в CI, семантика, ARIA, фокус, контраст, skip-link, декларация `/pieejamiba` |
| **Приватность** | **GDPR** (ЕС 2016/679), ePrivacy | Только необходимые cookie, cookie-уведомление, страница `/privatums`, права субъекта |
| **Мобильность** | Responsive, mobile-first, тач-таргеты (WCAG 2.5.8) | Проверка отсутствия горизонтального скролла на 360px, Lighthouse mobile |
| **Производительность/SEO/Best practices** | Lighthouse категории | Lighthouse CI с порогами |
| **Локализация** | LV/RU/EN | i18n-модуль, переключатель языка, `lang` атрибуты |
| **Интеграция** | Visma Horizon REST (NĪP/KNS) | Абстракция провайдера, mock для демо |

## 2. Автоматизация (ворота качества)

Проверки запускаются **на каждый push/PR** и **еженедельно** через GitHub Actions
(`deploy_extras/quality-gates.yml` → положить в `.github/workflows/`).

### 2.1 Доступность — `tools/audit/a11y.mjs`
- Поднимает приложение, проходит по **13 сценариям** (публичные + демо-вход всех
  ролей), прогоняет **axe-core** по тегам `wcag2a/2aa/21a/21aa/22aa`.
- Дополнительно проверяет **отсутствие горизонтального скролла на 360px**.
- **Падает (exit 1)**, если есть нарушения `serious`/`critical` или мобильный
  оверфлоу → PR нельзя влить с регрессией доступности.
- Локальный запуск: `cd tools/audit && npm i && node a11y.mjs`.

### 2.2 Lighthouse (mobile) — `tools/audit/lighthouserc.cjs`
- Мобильная эмуляция, пороги: accessibility ≥ 0.95 (error), best-practices/SEO ≥
  0.9, performance ≥ 0.5 (warn).
- Гоняется против live-сайта; отчёт публикуется во временное хранилище LHCI.

## 3. Слежение за новыми стандартами

- **Еженедельный CI-прогон** (cron) переустанавливает свежие axe-core и Lighthouse
  → новые правила и версии стандартов подхватываются автоматически; регрессии
  всплывают в отчёте.
- **Версии зафиксированы** в `tools/audit` (axe-core 4.10.x, LHCI 0.14.x) —
  обновление осознанное, через PR, чтобы видеть влияние новых правил.
- **Источники для ручного контроля новизны:**
  - WCAG: https://www.w3.org/TR/WCAG22/ (и черновики WCAG 3.0 / Silver)
  - ЕС веб-доступность: https://eur-lex.europa.eu/eli/dir/2016/2102/oj
  - GDPR: https://gdpr.eu/ · латвийский надзор: https://www.dvi.gov.lv
  - Latvija: MK noteikumi par tīmekļvietņu piekļūstamību
- Раз в квартал — ревизия этого документа и порогов.

## 4. Дашборд/наблюдаемость
- Артефакт `a11y-report.json` сохраняется в каждом прогоне CI (история регрессий).
- Lighthouse отчёты — ссылки в логах Actions.
- Health-эндпоинт `/api/health` + keep-alive (само-пинг и Actions).

## 5. Ручной чек-лист перед релизом (best practices)
- [ ] `node a11y.mjs` = 0 serious/critical
- [ ] Проверка с клавиатуры (Tab по всем интерактивным элементам, виден фокус)
- [ ] Проверка на реальном мобильном (портрет/ландшафт)
- [ ] Тексты переведены на LV/RU/EN
- [ ] Нет секретов в коде/логах
- [ ] Cookie/приватность актуальны

## 6. Дорожная карта усиления
- Прод-сборка Tailwind (убрать CDN-предупреждение, ускорить загрузку).
- Автотесты пользовательских сценариев (Playwright e2e) в тех же воротах.
- Реальный контраст-токенайзер (дизайн-токены) вместо ручных классов.
- Подключить `pa11y-ci`/`lighthouse-ci` server для трендов во времени.

---

## 7. Расширенная автоматизация безопасности и соответствия (v2)

Добавлено сверх доступности/Lighthouse:

| Проверка | Инструмент | Где | Гейт |
|---|---|---|---|
| Security headers | `tools/audit/check_headers.py` | CI (job accessibility) | ✅ падает при отсутствии |
| Уязвимости Python-зависимостей (CVE) | `pip-audit` | CI (job security) | ⚠️ warning |
| Секреты в коде/истории | `gitleaks` | CI (job security) | ✅ |
| Валидность HTML | `html-validate` | CI (job html-validate) | ⚠️ warning |
| Обновления зависимостей | **Dependabot** (`deploy_extras/dependabot.yml`) | еженедельно, авто-PR | — |
| Новые версии стандартов/инструментов | **standards-watch** (`deploy_extras/standards-watch.yml`) | еженедельно, авто-issue | — |

### Реестр соответствия
- **`compliance.yml`** — машиночитаемый реестр стандартов и законов со статусами
  (ok/partial/planned/n/a) и способом контроля каждого.
- Публичная страница **`/atbilstiba`** рендерит реестр (с автопометкой ⚙︎ auto для
  автоматически проверяемых пунктов).

### Security headers, которые отдаёт приложение
CSP, HSTS (HTTPS), X-Content-Type-Options, X-Frame-Options, Referrer-Policy,
Permissions-Policy, Cross-Origin-Opener-Policy. Сессионная cookie: HttpOnly +
Secure (прод) + SameSite=Lax.

## 8. Полная карта стандартов и законов (кратко)
Доступность: **WCAG 2.2 AA, EN 301 549, Дир. 2016/2102, EAA 2019/882, MK Nr. 445**.
Данные: **GDPR 2016/679, ePrivacy 2002/58, LV FPDAL**.
Безопасность: **OWASP Top 10 + Secure Headers, CVE-скан, NIS2 2022/2555, ISO 27001**.
Веб: **HTML Living Standard, Lighthouse, HTTPS/TLS**.
Цифровые ЕС: **eIDAS 910/2014, AI Act 2024/1689**.
Отрасль LV: **Ūdenssaimniecības pakalpojumu likums, MK Nr. 174, Dzīvojamo māju
pārvaldīšanas likums, Patērētāju tiesību aizsardzības likums**.
Полный список со статусами и ссылками — в `compliance.yml` и на `/atbilstiba`.
