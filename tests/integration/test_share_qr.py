"""Guard: страница «Поделиться» и QR‑эндпоинты работают.

Чтобы QR из справки (docs/QUICK_REFERENCE.md) не сломался незаметно.
"""
import pytest

pytestmark = pytest.mark.integration


def test_share_page_renders(client):
    r = client.get("/koplietosana")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("name", ["site", "app", "help"])
def test_qr_svg_endpoints(client, name):
    r = client.get(f"/qr/{name}.svg")
    assert r.status_code == 200
    assert "image/svg+xml" in r.headers["content-type"]
    assert "<svg" in r.text[:200]


def test_qr_unknown_name_404(client):
    r = client.get("/qr/does-not-exist.svg")
    assert r.status_code == 404
