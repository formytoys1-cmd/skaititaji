"""Юнит-тесты аутентификации (app/auth.py): хэш, проверка, authenticate."""
import pytest

from app.auth import authenticate, hash_password, verify_password
from app.models import UserRole

pytestmark = pytest.mark.unit


def test_hash_is_salted_and_verifies():
    h1 = hash_password("correct horse")
    h2 = hash_password("correct horse")
    # соль случайна → разные хэши для одного пароля
    assert h1 != h2
    assert h1.startswith("pbkdf2_sha256$120000$")
    assert verify_password("correct horse", h1)
    assert not verify_password("wrong", h1)


def test_verify_password_handles_malformed_hash():
    assert verify_password("x", "not-a-valid-hash") is False
    assert verify_password("x", "") is False


def test_authenticate_success(session, factory):
    org = factory.organization()
    user = factory.user(organization=org, email="alice@test.local",
                        password="s3cret-pass", role=UserRole.RESIDENT)
    got = authenticate(session, "alice@test.local", "s3cret-pass")
    assert got is not None and got.id == user.id


def test_authenticate_is_case_insensitive_email(session, factory):
    org = factory.organization()
    factory.user(organization=org, email="bob@test.local", password="pw12345")
    assert authenticate(session, "BOB@test.local", "pw12345") is not None


def test_authenticate_wrong_password_returns_none(session, factory):
    org = factory.organization()
    factory.user(organization=org, email="carol@test.local", password="right-pw")
    assert authenticate(session, "carol@test.local", "wrong-pw") is None


def test_authenticate_inactive_user_denied(session, factory):
    org = factory.organization()
    factory.user(organization=org, email="dave@test.local", password="pw",
                 is_active=False)
    assert authenticate(session, "dave@test.local", "pw") is None
