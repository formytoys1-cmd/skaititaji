"""Демо‑доступ в проде: публичные точки входа ведут на обычный вход /login,
а НЕ на /demo-login (который в проде отключён по SEC‑001).

Guard: если кто‑то снова повесит кнопку «Войти в демо» на /demo-login, демо
на боевом сервере отдаст 404 и сломается — этот тест это предотвращает.
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("path", ["/", "/demo", "/palidziba/instrukcija"])
def test_public_pages_do_not_link_to_bypass(client, path):
    r = client.get(path)
    if r.status_code == 404:
        pytest.skip(f"{path} нет в этой сборке")
    assert r.status_code == 200
    assert "/demo-login" not in r.text, (
        f"{path} ссылается на /demo-login — в проде это 404 (SEC‑001). "
        "Используйте /login?demo=<role>."
    )


def test_demo_page_links_to_login_prefill(client):
    r = client.get("/demo")
    assert r.status_code == 200
    for role in ("resident", "manager", "admin"):
        assert f"/login?demo={role}" in r.text


def test_login_page_has_demo_autofill(client):
    r = client.get("/login")
    assert r.status_code == 200
    # автозаполнение демо‑данных по ?demo=<role>
    assert "URLSearchParams" in r.text
    assert "resident@demo.lv" in r.text
