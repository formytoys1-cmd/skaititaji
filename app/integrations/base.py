"""Абстракция интеграции с учётной/ERP-системой.

Любой провайдер (Visma Horizon, Namejs, ZZ Dats и т.д.) реализует один
и тот же интерфейс. Это позволяет подключать новые системы, не меняя
код подачи показаний — только добавляя реализацию провайдера.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExternalMeter:
    external_id: str
    serial_number: str
    meter_type_code: str
    unit_external_id: Optional[str] = None
    last_value: Optional[float] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PushResult:
    ok: bool
    pushed: int = 0
    external_ids: list[str] = field(default_factory=list)
    message: str = ""
    raw: Any = None


class AccountingIntegration(ABC):
    """Базовый интерфейс провайдера учётной системы."""

    provider_code: str = "base"

    @abstractmethod
    def health_check(self) -> bool:
        """Проверка доступности и авторизации."""

    @abstractmethod
    def list_meters(self, object_external_id: Optional[str] = None) -> list[ExternalMeter]:
        """Получить список счётчиков (по объекту или все)."""

    @abstractmethod
    def push_readings(self, readings: list[dict[str, Any]]) -> PushResult:
        """Выгрузить показания. Каждый элемент:
        {external_meter_id, value, reading_date (ISO), period}."""
