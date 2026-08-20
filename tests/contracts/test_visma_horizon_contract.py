"""Контрактные тесты интеграции Visma Horizon (VISMA-001).

Проверяют, что клиент разбирает ответы в форме реальной схемы Horizon REST
(OpenAPI 3.0.1, версия 620.4): SL-сервисы `/query` и `/sync/*`, а также
BL-акт записи показаний `TdmPNSPnaSkaIzmBL` через шаблон.

Все HTTP-вызовы замоканы через `httpx.MockTransport` — реальная сеть НЕ
используется. Расхождение формы ответа со схемой должно ломать тест.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.integrations.visma_horizon import VismaHorizonClient

BASE_URL = "https://horizon.example.lv"


def _client(handler) -> VismaHorizonClient:
    transport = httpx.MockTransport(handler)
    return VismaHorizonClient(
        base_url=BASE_URL,
        username="svc",
        password="secret",
        mock=False,
        transport=transport,
    )


# --------------------------------------------------------------------------- #
# Реальная форма ответов Horizon (по OpenAPI-схеме сервисов SL/BL).
# --------------------------------------------------------------------------- #
READINGS_QUERY_RESPONSE = {
    "items": [
        {
            "Pk": 500101,
            "SkaitPk": 100501,
            "SerNr": "AK-2021-114455",
            "ObjektaId": "HZ-OBJ-1",
            "Radijums": 124.500,
            "RadDatums": "2026-08-01",
            "Periods": "2026-08",
        },
        {
            "Pk": 500102,
            "SkaitPk": 100502,
            "SerNr": "AK-2021-114456",
            "ObjektaId": "HZ-OBJ-1",
            "Radijums": 88.100,
            "RadDatums": "2026-08-01",
            "Periods": "2026-08",
        },
    ]
}

SYNC_NEW_RESPONSE = {
    "items": [
        {
            "Pk": 500103,
            "SkaitPk": 100503,
            "SerNr": "AK-2021-114457",
            "ObjektaId": "HZ-OBJ-2",
            "Radijums": 12.000,
            "RadDatums": "2026-08-19",
            "Periods": "2026-08",
        }
    ]
}

WRITE_TEMPLATE_RESPONSE = {"items": [{"Pk": 7001, "Nosaukums": "Rādījumu akts"}]}
WRITE_ACT_RESPONSE = {"Pk": 900123, "DokNr": "AKT-900123", "Status": "Created"}


def test_visma_read_contract():
    """SL `/query` показаний разбирается по реальной схеме (Pk/SerNr/Radijums…)."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/query")
        assert "TdmPNSSkaLigRadSL" in request.url.path
        # Basic-auth должен присутствовать.
        assert request.headers["authorization"].lower().startswith("basic ")
        return httpx.Response(200, json=READINGS_QUERY_RESPONSE)

    client = _client(handler)
    rows = client.read_readings(object_external_id="HZ-OBJ-1")

    assert len(rows) == 2
    first = rows[0]
    # Контракт: ключевые поля из схемы Horizon присутствуют и типизированы.
    assert first["external_reading_id"] == "500101"
    assert first["external_meter_id"] == "100501"
    assert first["serial_number"] == "AK-2021-114455"
    assert first["value"] == pytest.approx(124.5)
    assert first["reading_date"] == "2026-08-01"
    assert first["period"] == "2026-08"


def test_visma_write_act_contract():
    """Запись показания создаёт BL-акт TdmPNSPnaSkaIzmBL по шаблону.

    Проверяет форму payload (Rows[*] с SkaitPk/Radijums/RadDatums) и разбор
    ответа акта (Pk).
    """
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/template") and request.method == "GET":
            return httpx.Response(200, json=WRITE_TEMPLATE_RESPONSE)
        if "/template/7001" in path and request.method == "POST":
            body = json.loads(request.content)
            seen["payload"] = body
            assert "TdmPNSPnaSkaIzmBL" in path
            return httpx.Response(200, json=WRITE_ACT_RESPONSE)
        raise AssertionError(f"unexpected {request.method} {path}")

    client = _client(handler)
    result = client.push_readings(
        [
            {
                "external_meter_id": "100501",
                "value": 125.0,
                "reading_date": "2026-08-20",
                "period": "2026-08",
            }
        ]
    )

    assert result.ok is True
    assert result.pushed == 1
    assert result.external_ids == ["900123"]
    # Контракт payload: строки акта соответствуют схеме BL.
    row = seen["payload"]["Rows"][0]
    assert row["SkaitPk"] == "100501"
    assert row["Radijums"] == 125.0
    assert row["RadDatums"] == "2026-08-20"
    assert row["Periods"] == "2026-08"


def test_visma_sync_incremental():
    """Инкрементальная синхронизация через `/sync/new` разбирается по схеме."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sync/new")
        assert "TdmPNSSkaLigRadSL" in request.url.path
        return httpx.Response(200, json=SYNC_NEW_RESPONSE)

    client = _client(handler)
    rows = client.sync_readings()

    assert len(rows) == 1
    assert rows[0]["external_reading_id"] == "500103"
    assert rows[0]["value"] == pytest.approx(12.0)
    assert rows[0]["period"] == "2026-08"
