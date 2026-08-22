# Месячный самоулучшающийся контролёр (self-improve)

Автономный контролёр, объединяющий **аудит + контроль + оптимизацию + саморазвитие**,
запускается **раз в месяц** в облаке через **GitHub Actions schedule cron** (launchd не
используется — платформа Skaitītāji облачная).

- Мозг: [`tools/self_improve_controller.py`](../tools/self_improve_controller.py) —
  **детерминированный**, без вызова LLM (бесплатный, headless).
- Планировщик: [`.github/workflows/self-improve.yml`](../.github/workflows/self-improve.yml)
  — `cron: '0 4 1 * *'` (1-го числа месяца, 04:00 UTC) + `workflow_dispatch` (ручной запуск).
- Реестр возможностей/критериев: [`tools/self_improve/capabilities.json`](../tools/self_improve/capabilities.json).

## Фазы цикла

| Фаза | Что делает |
|------|-----------|
| **PRE** | Snapshot baseline-гейтов (pytest, ruff, покрытие). **baseline-red → abort** без правок (safe-on-failure). |
| **SELF-DEV** | Безопасные обратимые улучшения самого контролёра/окружения (`ruff --fix`). При регрессии — **авто-revert** (`git restore`), никогда не оставляет сломанным. |
| **DERIVE** | Выделяет применимое к проекту Skaitītāji. |
| **HANDOFF** | Безопасные обратимые правки применяются (с откатом); рискованные — в очередь предложений `docs/self_improve/proposals_YYYY-MM.md`. |
| **POST** | Журнал `data/self_improve/journal.jsonl` + heartbeat `data/self_improve/heartbeat.json` + отчёт. |

## Как проект принимает решения

- **Безопасные обратимые правки** → workflow открывает **Pull Request**
  (ветка `self-improve/monthly`, `peter-evans/create-pull-request`). Проект решает через **merge**.
- **Рискованные предложения** → открывается/дополняется **issue** с чекбоксами
  (без автомержа). Решает человек.

## Свойства

- **Отказоустойчивость**: baseline-red → только отчёт; авто-revert небезопасных правок.
- **Не ломает существующие тесты/CI**: контролёр не мержит сам, использует встроенный `GITHUB_TOKEN`.
- **Идемпотентность**: чистый прогон без фиксов не оставляет правок.
- **Секреты не раскрываются**.

## Ручной запуск

Actions → **self-improve** → Run workflow, либо локально:

```bash
python -m tools.self_improve_controller --report-out report.md
```

Тесты контролёра: `tests/unit/test_self_improve_controller.py`.
