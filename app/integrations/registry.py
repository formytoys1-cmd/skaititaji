"""Реестр провайдеров интеграций. Добавление нового провайдера — одна строка."""
from __future__ import annotations

from app.integrations.base import AccountingIntegration
from app.integrations.visma_horizon import VismaHorizonClient
from app.models import Organization

_PROVIDERS = {
    "visma_horizon": VismaHorizonClient,
}


def get_integration(org: Organization) -> AccountingIntegration:
    """Возвращает клиента интеграции для организации по её настройкам."""
    provider = org.integration_provider or "visma_horizon"
    cls = _PROVIDERS.get(provider, VismaHorizonClient)
    cfg = org.integration_config or {}
    return cls(
        base_url=cfg.get("base_url", ""),
        username=cfg.get("username", ""),
        password=cfg.get("password", ""),
        mock=cfg.get("mock"),
        endpoints=cfg.get("endpoints"),
    )
