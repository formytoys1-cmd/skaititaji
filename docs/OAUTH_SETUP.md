# Вход через проверенные сервисы (OAuth) — настройка

Позволяет жителям входить через **Google / Microsoft / GitHub** — без пароля,
e-mail уже подтверждён провайдером. Всё **бесплатно**. Провайдер включается, как
только заданы его `CLIENT_ID` и `CLIENT_SECRET` в переменных окружения (Render →
Environment). Секреты в репозиторий не попадают.

## Что видит пользователь
- На `/login` и `/registreties` появляются кнопки «Turpināt ar Google» и т.п.
  (только для настроенных провайдеров).
- Существующий аккаунт (совпал по e-mail) — сразу вход.
- Новый пользователь — после провайдера просим только **номер лицевого счёта**
  квартиры (`/registreties/pabeigt`), затем создаём подтверждённый аккаунт и
  привязываем к квартире (с учётом вместимости).

## Redirect URI (callback)
Для каждого провайдера в его консоли укажите точный адрес возврата:

    https://skaititaji.onrender.com/auth/<provider>/callback

напр. `https://skaititaji.onrender.com/auth/google/callback`
Локально: `http://127.0.0.1:8000/auth/google/callback`
(база берётся из `PUBLIC_BASE_URL` / `RENDER_EXTERNAL_URL`.)

## Google (рекомендуется, самый популярный в LV)
1. https://console.cloud.google.com → создать проект.
2. «APIs & Services» → «OAuth consent screen» → External → заполнить (app name,
   support email). Добавить scope `email`, `profile`, `openid`.
3. «Credentials» → «Create Credentials» → «OAuth client ID» → тип **Web
   application**. В «Authorized redirect URIs» добавить callback (см. выше).
4. Скопировать **Client ID** и **Client secret** → задать на Render:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
5. Redeploy. На `/login` появится кнопка Google.

## Microsoft (Azure AD)
1. https://portal.azure.com → Azure Active Directory → App registrations → New.
2. Redirect URI (Web) = callback (см. выше). Supported accounts: по вашему выбору.
3. Certificates & secrets → New client secret.
4. Env: `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`.

## GitHub
1. https://github.com/settings/developers → New OAuth App.
2. Authorization callback URL = callback (см. выше).
3. Env: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`.

## Безопасность
- **state** (анти-forgery) генерируется и хранится в подписанной сессии,
  проверяется в callback (constant-time). Чужой/battый state → отказ.
- Секреты только в env; провайдер выключен, пока не заданы оба ключа.
- Новый пользователь всё равно проходит привязку к квартире (account_number) и
  проверку вместимости — регистрация не обходит бизнес-правила.

## Добавить нового провайдера
Одна запись в `PRESETS` (`app/oauth.py`) с его authorize/token/userinfo URL и
scope — код обмена универсальный. Кнопка появится автоматически при заданных env.
