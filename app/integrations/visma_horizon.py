"""Клиент интеграции с Visma Horizon REST API.

Документация: https://horizon-rest-doc.visma.lv/lv
(подробный разбор см. в docs/research_visma_horizon.md)

Ключевые факты об API (OpenAPI 3.0.1, Horizon 620.4):
- **Хостинг on-premise:** базовый URL индивидуален для каждого клиента, вида
  ``https://<server>/API/rest/``.
- **Аутентификация:** HTTP Basic (пользователь Horizon с правами на модули
  NĪP «Nekustamo īpašumu pārvaldība» и KNS «Komunālo norēķinu sistēma»).
- **Формат:** JSON (и XML). Списочные сервисы (SL) поддерживают ``/query`` c
  параметрами filter/columns/orderby/limit и инкрементальную синхронизацию
  через ``/sync/new`` | ``/sync/changed``.
- **Модель:** документные сервисы (BL) — полный CRUD; списочные (SL) — чтение/sync.

Сервисы, relevantные для подачи показаний счётчиков (коды Horizon):
- Счётчики (NĪP):           TdmPNSSkaBL        (BL, CRUD)
- Счётчики (KNS):           TdmKNSkaBL         (BL, CRUD)
- Показания по договорам:   TdmPNSSkaLigRadSL  (SL, query/sync) — чтение
- Считанные показания:      TdmPNSSkaNolRadSL  (SL, query/sync) — чтение
- Запись показаний:         TdmPNSPnaSkaIzmBL  (BL, акт изменения) — запись
- Клиенты/абоненты:         TdmPNSKlientsBL    (BL)
- Договоры:                 TdmPNSWEBClientContractsSL (SL)
- Квартиры (telpu grupa):   TdmPNSTGBL         (BL)
- Счета:                    TdmPNSRekBL        (BL)
- Health check:             GET /API/rest/global/healthCheck

Все коды сервисов вынесены в ``endpoints`` и переопределяемы через настройки
организации, т.к. состав модулей у клиентов различается.

Для демо по умолчанию включён MOCK-режим (``settings.visma_mock``): ответы API
эмулируются, чтобы платформа работала без реального сервера Horizon.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from app.config import settings
from app.integrations.base import (
    AccountingIntegration,
    ExternalMeter,
    PushResult,
)

# Коды REST-сервисов Horizon по умолчанию (переопределяемы в integration_config).
DEFAULT_ENDPOINTS = {
    "health": "/API/rest/global/healthCheck",
    "meters_nip": "/API/rest/TdmPNSSkaBL",
    "meters_kns": "/API/rest/TdmKNSkaBL",
    "meters_list": "/API/rest/TdmPNSSkaEksSL",
    "readings_query": "/API/rest/TdmPNSSkaLigRadSL",
    "readings_read": "/API/rest/TdmPNSSkaNolRadSL",
    "readings_write_act": "/API/rest/TdmPNSPnaSkaIzmBL",
    "customers": "/API/rest/TdmPNSKlientsBL",
    "contracts": "/API/rest/TdmPNSWEBClientContractsSL",
    "units": "/API/rest/TdmPNSTGBL",
    "invoices": "/API/rest/TdmPNSRekBL",
}


class VismaHorizonClient(AccountingIntegration):
    provider_code = "visma_horizon"

    def __init__(
        self,
        base_url: str = "",
        username: str = "",
        password: str = "",
        *,
        mock: Optional[bool] = None,
        endpoints: Optional[dict[str, str]] = None,
        timeout: float = 20.0,
        transport: Optional[httpx.BaseTransport] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.base_url = (base_url or settings.visma_base_url).rstrip("/")
        self.username = username or settings.visma_username
        self.password = password or settings.visma_password
        self.mock = settings.visma_mock if mock is None else mock
        self.endpoints = {**DEFAULT_ENDPOINTS, **(endpoints or {})}
        self.timeout = timeout
        # Транспорт инъектируется в тестах (httpx.MockTransport), в проде — None.
        self._transport = transport
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    # --------------------------------------------------------------------- #
    # HTTP helpers
    # --------------------------------------------------------------------- #
    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            auth=(self.username, self.password),
            timeout=self.timeout,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            transport=self._transport,
        )

    def _request(
        self, client: httpx.Client, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Выполняет HTTP-запрос и поднимает ошибку на 4xx/5xx.

        (Ретраи/backoff добавляются в VISMA-002.)
        """
        r = client.request(method, url, **kwargs)
        r.raise_for_status()
        return r

    @staticmethod
    def _items(data: Any) -> list[dict]:
        if isinstance(data, dict):
            for key in ("items", "Items", "data", "rows"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return data if isinstance(data, list) else []

    # --------------------------------------------------------------------- #
    # Interface
    # --------------------------------------------------------------------- #
    def health_check(self) -> bool:
        if self.mock:
            return True
        try:
            with self._client() as c:
                r = c.get(self.endpoints["health"])
            return r.status_code < 400
        except Exception:
            return False

    def list_meters(
        self, object_external_id: Optional[str] = None
    ) -> list[ExternalMeter]:
        if self.mock:
            return self._mock_meters(object_external_id)
        params: dict[str, Any] = {"hierarchy": "false", "limit": 500}
        if object_external_id:
            params["filter"] = f"ObjektaId={object_external_id}"
        with self._client() as c:
            r = c.get(f"{self.endpoints['meters_list']}/query", params=params)
            r.raise_for_status()
            data = r.json()
        result: list[ExternalMeter] = []
        for it in self._items(data):
            result.append(
                ExternalMeter(
                    external_id=str(it.get("Pk") or it.get("Id") or ""),
                    serial_number=str(it.get("SerNr") or it.get("Numurs") or ""),
                    meter_type_code=str(it.get("Veids") or "cold_water"),
                    unit_external_id=str(it.get("ObjektaId") or "") or None,
                    last_value=it.get("PedRadijums"),
                    extra=it,
                )
            )
        return result

    # --------------------------------------------------------------------- #
    # Чтение показаний (SL query / инкрементальный sync)
    # --------------------------------------------------------------------- #
    @staticmethod
    def _reading_row(it: dict) -> dict[str, Any]:
        """Нормализует запись показания SL-сервиса в контрактную форму."""
        return {
            "external_reading_id": str(it.get("Pk") or ""),
            "external_meter_id": str(it.get("SkaitPk") or ""),
            "serial_number": str(it.get("SerNr") or "") or None,
            "unit_external_id": str(it.get("ObjektaId") or "") or None,
            "value": it.get("Radijums"),
            "reading_date": it.get("RadDatums"),
            "period": it.get("Periods"),
            "extra": it,
        }

    def read_readings(
        self, object_external_id: Optional[str] = None, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Читает показания по договорам через SL `/query` (TdmPNSSkaLigRadSL)."""
        params: dict[str, Any] = {"hierarchy": "false", "limit": limit}
        if object_external_id:
            params["filter"] = f"ObjektaId={object_external_id}"
        with self._client() as c:
            r = self._request(c, "GET", f"{self.endpoints['readings_query']}/query",
                              params=params)
            data = r.json()
        return [self._reading_row(it) for it in self._items(data)]

    def sync_readings(self, mode: str = "new") -> list[dict[str, Any]]:
        """Инкрементальная синхронизация показаний через `/sync/{mode}`.

        mode ∈ {"new", "changed", "edited", "deleted"}.
        """
        with self._client() as c:
            r = self._request(
                c, "GET", f"{self.endpoints['readings_query']}/sync/{mode}"
            )
            data = r.json()
        return [self._reading_row(it) for it in self._items(data)]

    def push_readings(self, readings: list[dict[str, Any]]) -> PushResult:
        """Записывает показания как акт изменения счётчиков (TdmPNSPnaSkaIzmBL).

        SL-сервисы показаний (TdmPNSSkaLigRadSL / ...NolRadSL) доступны только на
        чтение, поэтому запись выполняется через BL-акт по шаблону.
        """
        if self.mock:
            return self._mock_push(readings)
        act = self.endpoints["readings_write_act"]
        pushed, ext_ids = 0, []
        with self._client() as c:
            tmpl = c.get(f"{act}/template")
            tmpl.raise_for_status()
            templates = self._items(tmpl.json())
            tmpl_pk = templates[0].get("Pk") if templates else None

            rows = [
                {
                    "SkaitPk": rd["external_meter_id"],
                    "Radijums": rd["value"],
                    "RadDatums": rd["reading_date"],
                    "Periods": rd.get("period"),
                }
                for rd in readings
            ]
            payload = {"Rows": rows}
            url = f"{act}/template/{tmpl_pk}" if tmpl_pk else act
            r = c.post(url, json=payload)
            r.raise_for_status()
            body = r.json() if r.content else {}
            pushed = len(rows)
            ext_ids.append(str(body.get("Pk", "")))
        return PushResult(ok=True, pushed=pushed, external_ids=ext_ids,
                          message=f"Izveidots rādījumu akts ({pushed} rādījumi)")

    # --------------------------------------------------------------------- #
    # Mock implementation (демо без реального Horizon)
    # --------------------------------------------------------------------- #
    def _mock_meters(self, object_external_id: Optional[str]) -> list[ExternalMeter]:
        return [
            ExternalMeter(
                external_id="HZ-M-1001",
                serial_number="AK-2021-114455",
                meter_type_code="cold_water",
                unit_external_id=object_external_id or "HZ-OBJ-1",
                last_value=123.456,
            ),
            ExternalMeter(
                external_id="HZ-M-1002",
                serial_number="AK-2021-114456",
                meter_type_code="hot_water",
                unit_external_id=object_external_id or "HZ-OBJ-1",
                last_value=87.201,
            ),
        ]

    def _mock_push(self, readings: list[dict[str, Any]]) -> PushResult:
        ext_ids = [f"HZ-R-{9000 + i}" for i, _ in enumerate(readings)]
        return PushResult(
            ok=True,
            pushed=len(readings),
            external_ids=ext_ids,
            message=f"[MOCK] Uz Visma Horizon nosūtīti {len(readings)} rādījumi "
                    "(akts TdmPNSPnaSkaIzmBL)",
            raw={"mock": True, "count": len(readings), "act": "TdmPNSPnaSkaIzmBL"},
        )
