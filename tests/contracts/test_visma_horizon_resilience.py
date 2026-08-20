"""Тесты устойчивости интеграции Visma Horizon (VISMA-002).

Проверяют ретраи с экспоненциальным backoff на идемпотентных операциях,
идемпотентную запись показаний при обрыве после отправки (без дубля акта),
и обработку 4xx/5xx. Всё на моках httpx — без реальной сети.
"""
from __future__ import annotations

import httpx
import pytest

from app.integrations.visma_horizon import VismaHorizonClient

BASE_URL = "https://horizon.example.lv"


def _client(handler, **kw) -> VismaHorizonClient:
    transport = httpx.MockTransport(handler)
    return VismaHorizonClient(
        base_url=BASE_URL,
        username="svc",
        password="secret",
        mock=False,
        transport=transport,
        backoff_factor=0.0,  # без реальных пауз в тестах
        **kw,
    )


QUERY_OK = {"items": [{"Pk": 1, "SkaitPk": 10, "Radijums": 5.0,
                       "RadDatums": "2026-08-01", "Periods": "2026-08"}]}
TEMPLATE_OK = {"items": [{"Pk": 7001}]}
ACT_OK = {"Pk": 900123}


def test_visma_retry_on_5xx():
    """GET-чтение ретраится на 5xx и завершается успехом на 3-й попытке."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, json={"error": "service unavailable"})
        return httpx.Response(200, json=QUERY_OK)

    client = _client(handler, max_retries=3)
    rows = client.read_readings()

    assert calls["n"] == 3
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(5.0)


def test_visma_no_retry_on_4xx():
    """4xx (кроме 429) не ретраится — сразу поднимается ошибка."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad request"})

    client = _client(handler, max_retries=3)
    with pytest.raises(httpx.HTTPStatusError):
        client.read_readings()
    assert calls["n"] == 1


def test_visma_write_idempotent_on_timeout():
    """Обрыв (таймаут) после отправки акта не создаёт дубль.

    Первая POST-попытка «обрывается» (ReadTimeout) уже после того, как сервер
    принял запрос. Ретрай отправляется с тем же Idempotency-Key, и сервер
    возвращает тот же существующий акт — второго акта не создаётся.
    """
    state = {"acts": {}, "posts": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/template"):
            return httpx.Response(200, json=TEMPLATE_OK)
        if request.method == "POST":
            state["posts"] += 1
            key = request.headers.get("idempotency-key")
            assert key, "запись должна нести Idempotency-Key"
            # Первый раз: сервер уже принял, но ответ теряется (таймаут).
            if state["posts"] == 1:
                state["acts"][key] = 900123
                raise httpx.ReadTimeout("connection dropped", request=request)
            # Ретрай с тем же ключом: возвращаем существующий акт, не создаём новый.
            assert key in state["acts"]
            return httpx.Response(200, json={"Pk": state["acts"][key]})
        raise AssertionError(f"unexpected {request.method} {path}")

    client = _client(handler, max_retries=3)
    result = client.push_readings(
        [
            {
                "external_meter_id": "10",
                "value": 5.0,
                "reading_date": "2026-08-20",
                "period": "2026-08",
            }
        ]
    )

    assert result.ok is True
    assert result.external_ids == ["900123"]
    # Ровно один логический акт, несмотря на две физические попытки.
    assert state["posts"] == 2
    assert len(state["acts"]) == 1
