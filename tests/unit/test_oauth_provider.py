"""OAuth-провайдер: обмен code→token→userinfo (httpx замокан)."""
import httpx
import pytest

from app.auth_providers.base import AuthError
from app.auth_providers.oauth import OAuthProvider
from app.oauth import get_provider_config

pytestmark = pytest.mark.unit


def _google_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_authorize_url_contains_params(monkeypatch):
    _google_env(monkeypatch)
    cfg = get_provider_config("google")
    p = OAuthProvider(cfg)
    url = p.authorize_url("https://app/auth/google/callback", "state123")
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=cid" in url
    assert "state=state123" in url
    assert "redirect_uri=https%3A%2F%2Fapp%2Fauth%2Fgoogle%2Fcallback" in url
    assert "scope=openid" in url


def test_exchange_returns_identity(monkeypatch):
    _google_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "tok", "token_type": "Bearer"})
        if "userinfo" in str(request.url):
            return httpx.Response(200, json={
                "sub": "google-uid-1", "email": "New.User@Gmail.com",
                "name": "New User", "email_verified": True,
            })
        return httpx.Response(404)

    cfg = get_provider_config("google")
    p = OAuthProvider(cfg, client=_mock_client(handler))
    identity = p.exchange("authcode", "https://app/auth/google/callback")
    assert identity.provider == "google"
    assert identity.subject == "google-uid-1"
    assert identity.email == "new.user@gmail.com"  # нормализован
    assert identity.full_name == "New User"


def test_exchange_no_token_raises(monkeypatch):
    _google_env(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "invalid_grant"})

    cfg = get_provider_config("google")
    p = OAuthProvider(cfg, client=_mock_client(handler))
    with pytest.raises(AuthError):
        p.exchange("badcode", "https://app/auth/google/callback")


def test_from_code_disabled_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    with pytest.raises(AuthError):
        OAuthProvider.from_code("google")


def test_github_fetches_primary_email(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "cid")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/access_token"):
            return httpx.Response(200, json={"access_token": "tok"})
        if path == "/user":
            return httpx.Response(200, json={"id": 4242, "name": "Octo", "email": None})
        if path == "/user/emails":
            return httpx.Response(200, json=[
                {"email": "sec@x.io", "primary": False, "verified": True},
                {"email": "octo@x.io", "primary": True, "verified": True},
            ])
        return httpx.Response(404)

    cfg = get_provider_config("github")
    p = OAuthProvider(cfg, client=_mock_client(handler))
    identity = p.exchange("code", "https://app/auth/github/callback")
    assert identity.subject == "4242"
    assert identity.email == "octo@x.io"
