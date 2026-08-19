# Деплой на Render.com — вы уже на нужном экране

Вы вошли в Render (Marina's workspace) и на шаге «Create a new Web Service».

## Шаг 1 — Choose service
Нажмите **Web Services → «New Web Service →»** (динамическое приложение).
НЕ «Static Sites» (это для статики), не «Private Services», не «Background Workers».

## Шаг 2 — нужен Git-репозиторий
Render деплоит из Git. Если репозитория с кодом ещё нет — сначала залейте код на
GitHub (тем же входом через Google).

### Как залить код на GitHub (правильно)
1. github.com → «New repository» → имя `skaititaji` → **Public** → Create.
2. На странице пустого репозитория → **«uploading an existing file»**.
3. ВАЖНО: GitHub-загрузчик **НЕ распаковывает .zip**. Перетаскивайте
   **распакованные файлы и папки**, а не архив.
   Готовая распакованная папка лежит здесь (в файлах сессии):
   `.../session-state/<id>/files/skaititaji_upload/`
   Откройте её, выделите всё содержимое (app, docs, tools, render.yaml,
   requirements.txt, Dockerfile, README.md, …) и перетащите в окно загрузки GitHub.
4. Внизу нажмите **Commit changes**.

> Через консоль (если удобнее): в папке проекта
> `git remote add origin https://github.com/<логин>/skaititaji.git && git push -u origin main`

## Шаг 3 — Configure (Render заполнит из render.yaml)
- **Language:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Instance Type:** **Free**

Нажмите **Deploy Web Service**.

## Шаг 4 — Готово
Через ~2 минуты Render даст публичный адрес `https://skaititaji-...onrender.com`.
Демо-доступы: `admin@demo.lv` / `resident@demo.lv` / `manager@demo.lv`, пароль
`demo1234`, страница `/demo`. Бесплатный инстанс «засыпает» при простое — первый
запрос будит его за ~30 сек.
