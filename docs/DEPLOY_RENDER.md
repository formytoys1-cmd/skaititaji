# Деплой за 5 шагов через ваш Google-аккаунт (Render.com, бесплатно, без карты)

Пароль от Gmail никому вводить не нужно — вы просто входите в Render кнопкой
«Sign in with Google». Всё готово к деплою: в проекте есть [`render.yaml`](../render.yaml).

## Шаги

1. **GitHub (вход через Google).** Откройте github.com → «Sign up»/«Sign in» и
   войдите через ваш Google‑аккаунт `formytoys1@gmail.com`. Создайте новый
   **пустой** репозиторий, например `skaititaji`.

2. **Загрузите код.** Два способа:
   - **Просто (без консоли):** на странице репозитория → «uploading an existing
     file» → перетащите содержимое архива `skaititaji_deploy.zip` (я его
     подготовил, см. ниже) → Commit.
   - **Через консоль:** в папке проекта выполните
     ```bash
     git remote add origin https://github.com/<ваш-логин>/skaititaji.git
     git push -u origin main
     ```

3. **Render (вход через Google).** Откройте dashboard.render.com → «Sign in with
   Google» тем же аккаунтом.

4. **Создайте сервис.** «New +» → **Blueprint** → выберите ваш репозиторий
   `skaititaji`. Render прочитает `render.yaml` и сам настроит web‑сервис
   (бесплатный план). Нажмите «Apply».

5. **Готово.** Через пару минут Render даст публичный адрес вида
   `https://skaititaji-demo.onrender.com`. Демо‑доступы прежние
   (`admin@demo.lv` / `demo1234`, страница `/demo`).

> Бесплатный инстанс «засыпает» при простое — первый запрос будит его за
> несколько секунд. Каждый `git push` авто‑деплоит новую версию.

## Ещё проще — доверить деплой мне

Если не хотите кликать сами, дайте мне **отзываемые токены** (не пароль):
- **GitHub Fine‑grained token** (права `Contents: R/W`, `Administration: R/W`) —
  я создам репозиторий и залью код.
- **Render API key** (dashboard.render.com → Account Settings → API Keys) —
  я создам сервис из репозитория.

Вставьте их в чат — я задеплою и скажу URL, после чего вы сразу отзовёте токены.
В репозиторий/логи токены не попадают.
