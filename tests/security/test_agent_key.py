"""SEC-007 — сравнение ключа агента должно быть constant-time.

Прямое сравнение `x_agent_key != settings.agent_api_key` уязвимо к timing-атаке
(подбор ключа по времени ответа). Требуется hmac.compare_digest.
"""
import inspect

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.security


def test_agent_key_uses_constant_time_compare(monkeypatch):
    from app.routers import agent_api

    # Guard: код действительно использует постоянное по времени сравнение.
    src = inspect.getsource(agent_api.require_agent)
    assert "compare_digest" in src
    assert "!=" not in src

    monkeypatch.setattr(agent_api.settings, "agent_api_key", "s3cr3t-agent-key")

    # Неверный ключ → 401.
    with pytest.raises(HTTPException) as exc:
        agent_api.require_agent("wrong-key")
    assert exc.value.status_code == 401

    # Пустой ключ на сервере → API отключён (503) независимо от заголовка.
    monkeypatch.setattr(agent_api.settings, "agent_api_key", "")
    with pytest.raises(HTTPException) as exc2:
        agent_api.require_agent("whatever")
    assert exc2.value.status_code == 503


def test_agent_key_accepts_correct_key(monkeypatch):
    from app.routers import agent_api

    monkeypatch.setattr(agent_api.settings, "agent_api_key", "s3cr3t-agent-key")
    # Верный ключ → без исключения.
    assert agent_api.require_agent("s3cr3t-agent-key") is None
