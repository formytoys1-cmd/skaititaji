"""SEC-006: rate-limiting и анти-enumeration на аутентификации.

- >N неверных попыток входа за окно → HTTP 429.
- Ответ не раскрывает, существует ли email (одинаковый результат для
  существующего и несуществующего пользователя).
"""
import pytest

from app.models import UserRole

pytestmark = pytest.mark.security

PW = "pw-abcdef"


@pytest.fixture(autouse=True)
def _reset_limiter():
    from app.ratelimit import auth_limiter
    auth_limiter.clear()
    yield
    auth_limiter.clear()


def _csrf(client):
    import re
    html = client.get("/login").text
    return re.search(r'name="csrf_token"\s+value="([^"]+)"', html).group(1)


def test_login_rate_limited(client, session, factory):
    org = factory.organization()
    factory.user(organization=org, email="rl@test.local",
                 password=PW, role=UserRole.MANAGER)
    token = _csrf(client)
    statuses = []
    for _ in range(8):
        r = client.post(
            "/login",
            data={"email": "rl@test.local", "password": "wrong-pass",
                  "csrf_token": token},
            follow_redirects=False,
        )
        statuses.append(r.status_code)
    assert 429 in statuses, f"expected a 429 after too many attempts, got {statuses}"


def test_login_no_user_enumeration(client, session, factory):
    org = factory.organization()
    factory.user(organization=org, email="exists@test.local",
                 password=PW, role=UserRole.MANAGER)
    token = _csrf(client)

    # Существующий email, неверный пароль
    r_exists = client.post(
        "/login",
        data={"email": "exists@test.local", "password": "wrong-pass",
              "csrf_token": token},
        follow_redirects=False,
    )
    # Несуществующий email
    r_absent = client.post(
        "/login",
        data={"email": "nobody@test.local", "password": "wrong-pass",
              "csrf_token": token},
        follow_redirects=False,
    )
    # Ответы неотличимы: тот же статус и та же цель редиректа.
    assert r_exists.status_code == r_absent.status_code
    assert r_exists.headers.get("location") == r_absent.headers.get("location") == "/login"
