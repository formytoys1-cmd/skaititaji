"""SEC-005: CSRF-защита мутирующих POST-форм.

Проверяем, что POST без валидного CSRF-токена отклоняется (403), а с валидным
токеном (полученным из формы входа) — проходит.
"""
import re

import pytest

from app.models import UserRole

pytestmark = pytest.mark.security

PW = "pw-123456"


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert m, "CSRF hidden field not found in rendered form"
    return m.group(1)


def test_post_without_csrf_rejected(client, session, factory):
    org = factory.organization()
    factory.user(organization=org, email="c1@test.local",
                 password=PW, role=UserRole.MANAGER)
    r = client.post(
        "/login",
        data={"email": "c1@test.local", "password": PW},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_post_with_csrf_ok(client, session, factory):
    org = factory.organization()
    factory.user(organization=org, email="c2@test.local",
                 password=PW, role=UserRole.MANAGER)
    form = client.get("/login")
    token = _extract_csrf(form.text)
    r = client.post(
        "/login",
        data={"email": "c2@test.local", "password": PW,
              "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/parvalde"
