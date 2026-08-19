# Как сделать, чтобы сайт не «засыпал» (Render Free)

Бесплатный инстанс Render выключается после ~15 мин простоя; первый запрос
после этого идёт 30–50 сек. Чтобы держать его «тёплым», нужно пинговать
`/api/health` каждые ~10 минут. Бесплатный способ — GitHub Actions (cron).

Файл workflow уже готов: `deploy_extras/keepalive.yml`.

## Вариант 1 — добавить через сайт GitHub (1 минута, без токена)
1. Откройте репозиторий: https://github.com/formytoys1-cmd/skaititaji
2. Кнопка **Add file → Create new file**.
3. В поле имени введите: `.github/workflows/keepalive.yml`
4. Вставьте содержимое файла `deploy_extras/keepalive.yml` (см. ниже).
5. Внизу **Commit changes**. Готово — Actions начнёт пинговать сайт.

## Вариант 2 — я сделаю сам
Пришлите GitHub-токен со scope **`workflow`** (github.com/settings/tokens →
classic → галочки `repo` и `workflow`) — я запушу workflow, и всё заработает.

## Содержимое keepalive.yml
```yaml
name: keep-alive
on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch: {}
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping health endpoint
        run: |
          for i in 1 2 3; do
            code=$(curl -s -o /dev/null -w "%{http_code}" https://skaititaji.onrender.com/api/health || echo 000)
            echo "attempt $i -> $code"
            [ "$code" = "200" ] && exit 0
            sleep 20
          done
          echo "site did not respond 200 (may be cold-starting)"; exit 0
```

> Примечание: планировщик GitHub Actions может запускать cron с задержкой в
> несколько минут — для «прогрева» это не критично.
