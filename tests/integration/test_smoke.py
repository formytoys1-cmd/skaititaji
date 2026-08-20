"""Smoke-тесты: приложение стартует и отдаёт публичные API (QA-001, Часть 3.3)."""
import pytest

pytestmark = pytest.mark.smoke


def test_app_starts_and_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "app" in body and "version" in body


def test_meter_types_endpoint(client):
    r = client.get("/api/meter-types")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # демо-сид создаёт базовые типы счётчиков
    assert len(data) >= 1
    sample = data[0]
    assert {"code", "category", "name", "unit"} <= set(sample.keys())


def test_organizations_endpoint(client):
    r = client.get("/api/organizations")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert {"slug", "name", "kind"} <= set(data[0].keys())


def test_landing_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_unknown_api_route_is_404_json(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.json()["detail"] == "Not found"
