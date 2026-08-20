# Skaitītāji — платформа подачи показаний счётчиков

Удобная, расширяемая, **мультиарендная** SaaS‑платформа для подачи показаний
счётчиков воды (холодной/горячей) и любых других типов счётчиков. Заточена под
латвийский рынок ЖКХ, с интеграцией **Visma Horizon REST API**.

> Это рабочая демо‑версия (MVP). Глубокий анализ рынка, законов и API, а также
> техническое задание — в папке [`docs/`](docs/).

## Возможности

- 🧩 **Config‑driven типы счётчиков** — новый тип (электричество, газ, тепло)
  добавляется как данные, без изменения кода.
- 🏢 **Мультиарендность** — каждая организация (управляющий, кооператив, водовод)
  изолирована, со своим брендом, окном подачи и интеграцией.
- 💧 **Подача воды ХВС/ГВС** — карточки счётчиков, предыдущее показание,
  live‑расчёт расхода, валидация и детекция аномалий.
- 🧑‍💼 **Кабинет управляющего** — прогресс подачи, аномалии, выгрузка в Visma Horizon.
- 🔌 **Интеграция Visma Horizon** — модули NĪP/KNS; в демо работает mock‑режим.
- 🌐 **Открытый API** — `/api/health`, `/api/meter-types`, `/api/organizations`.

## Быстрый старт

```bash
./run.sh
```

Скрипт создаёт виртуальное окружение, ставит зависимости, засевает демо‑данные и
запускает сервер (порт выбирается автоматически, начиная с 8000 — если занят,
берётся следующий свободный).

Фоновый запуск/остановка (без конфликтов портов, с PID‑файлом):

```bash
./tools/start.sh   # поднимает сервер в фоне, печатает выбранный порт
./tools/stop.sh    # останавливает
```

Вручную:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed                       # демо-данные (идемпотентно)
uvicorn app.main:app --reload
```

## Демо‑доступы (пароль у всех `demo1234`)

| Роль | E‑mail | Что показывает |
|---|---|---|
| Житель | `resident@demo.lv` | Подача показаний ХВС/ГВС |
| Житель | `anna@demo.lv`, `peteris@demo.lv` | Другие квартиры того же дома |
| Управляющий | `manager@demo.lv` | Дашборд + синхронизация с Visma Horizon |
| Админ / модератор | `admin@demo.lv` | Организации, типы счётчиков, **консоль обратной связи** |

Открыть `/demo` — страница с кнопками. Кнопки ведут на `/login?demo=<role>`
(`resident` / `manager` / `admin`): форма входа открывается с **уже
заполненными** e‑mail и паролем — остаётся нажать «Войти».

> **Безопасность (SEC‑001).** В проде вход в один клик через `/demo-login`
> (обход аутентификации) **отключён** — он вернёт 404. Демо работает через
> обычный вход реальными демо‑аккаунтами (хеш пароля, rate‑limit, CSRF).
> В локальной разработке (`DEBUG=1`) `/demo-login` по‑прежнему доступен.
> Управляется флагом `ALLOW_DEMO_LOGIN` (в проде должен быть `0`).

## Консоль модератора (обратная связь агенту)

Админ заходит в **Konsole** (`/admin/inbox`) и отправляет указания на доработку
(полную/частичную), с приоритетом и зоной. Указание доставляется запущенному
агенту через watcher‑мост, агент отвечает прямо в треде. Если что‑то неясно —
агент переводит тред в «Gaida precizējumu» и задаёт вопрос.

Инструменты агента:

```bash
python -m tools.feedback_watch          # фоновый мост: ждёт новые указания и уведомляет агента
python -m tools.agent_feedback pending  # список указаний, требующих внимания
python -m tools.agent_feedback show <id>
python -m tools.agent_feedback take <id>
python -m tools.agent_feedback review <id> "что сделано"
python -m tools.agent_feedback ask <id> "уточняющий вопрос"
```

## Деплой

См. [docs/DEPLOY.md](docs/DEPLOY.md): Google Cloud Run (`tools/deploy_cloudrun.sh`),
Render.com (`render.yaml`), Docker (`Dockerfile`). Приложение слушает `$PORT` и
переключается на PostgreSQL через `DATABASE_URL`.

## Структура

```
app/
  main.py              # сборка FastAPI, открытый API
  config.py            # настройки из окружения
  models.py            # модель данных (multi-tenant, config-driven типы)
  services.py          # бизнес-логика подачи (валидация, расход, аномалии)
  auth.py              # аутентификация (PBKDF2 + cookie-сессии)
  seed.py              # каталог типов счётчиков + демо-данные
  web.py               # рендеринг шаблонов + flash-сообщения
  integrations/
    base.py            # абстракция AccountingIntegration
    visma_horizon.py   # клиент Visma Horizon REST (+ mock)
    registry.py        # реестр провайдеров
  routers/             # public, auth, resident, manager, admin
  templates/           # Jinja2 + Tailwind (CDN)
docs/
  TZ.md                        # техническое задание
  research_water_suppliers.md  # водоводы и законы ЛР
  research_competitors.md      # анализ конкурентов
  research_visma_horizon.md    # разбор Visma Horizon REST API
```

## Настройка интеграции Visma Horizon

По умолчанию — mock (демо без реального сервера). Для подключения реального
Horizon задайте переменные окружения (см. [`.env.example`](.env.example)):

```
VISMA_MOCK=0
VISMA_BASE_URL=https://<ваш-сервер>/API/rest
VISMA_USERNAME=<пользователь Horizon>
VISMA_PASSWORD=<пароль>
```

Аутентификация — HTTP Basic; пользователю нужны права на модули NĪP и KNS.
Подробности эндпоинтов — в [docs/research_visma_horizon.md](docs/research_visma_horizon.md).

## Добавление нового типа счётчика

Через кабинет админа (`/admin`) или строкой в каталоге `DEFAULT_METER_TYPES`
([app/seed.py](app/seed.py)). Никаких изменений в логике подачи не требуется.

## Технологии

Python · FastAPI · SQLModel/SQLAlchemy · Jinja2 · Tailwind CSS · SQLite (→ PostgreSQL).
