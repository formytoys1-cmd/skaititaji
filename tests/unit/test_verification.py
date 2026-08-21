"""Сервис подтверждения e-mail: выпуск и проверка токенов."""
from datetime import datetime, timedelta

import pytest

from app.models import EmailVerification, User
from app.verification import create_verification, verify_token

pytestmark = pytest.mark.unit


def _make_user(session, verified=False):
    u = User(email=f"v{datetime.utcnow().timestamp()}@test.local",
             full_name="Test", password_hash="x", is_verified=verified)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def test_create_and_verify(session):
    user = _make_user(session)
    ev = create_verification(session, user)
    assert ev.token and ev.used_at is None
    verified = verify_token(session, ev.token)
    assert verified is not None
    assert verified.id == user.id
    assert verified.is_verified is True
    assert verified.verified_at is not None


def test_token_single_use(session):
    user = _make_user(session)
    ev = create_verification(session, user)
    assert verify_token(session, ev.token) is not None
    # повторное использование — отказ
    assert verify_token(session, ev.token) is None


def test_expired_token_rejected(session):
    user = _make_user(session)
    ev = create_verification(session, user)
    ev.expires_at = datetime.utcnow() - timedelta(minutes=1)
    session.add(ev)
    session.commit()
    assert verify_token(session, ev.token) is None


def test_unknown_token_rejected(session):
    assert verify_token(session, "does-not-exist") is None
    assert verify_token(session, "") is None


def test_wrong_purpose_rejected(session):
    user = _make_user(session)
    ev = EmailVerification(
        user_id=user.id, token="abc123", purpose="reset_password",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    session.add(ev)
    session.commit()
    # ожидаем purpose=verify_email по умолчанию
    assert verify_token(session, "abc123") is None
