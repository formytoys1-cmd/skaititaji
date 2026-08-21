"""Сервис подтверждения e-mail: выпуск и проверка одноразовых токенов."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models import EmailVerification, User


def create_verification(
    session: Session, user: User, *, purpose: str = "verify_email",
    ttl_hours: int = 24,
) -> EmailVerification:
    """Создаёт новый токен подтверждения для пользователя."""
    token = secrets.token_urlsafe(32)
    ev = EmailVerification(
        user_id=user.id,
        token=token,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def verify_token(
    session: Session, token: str, *, purpose: str = "verify_email",
) -> User | None:
    """Проверяет токен. При успехе помечает его использованным, пользователя —
    подтверждённым, и возвращает User. Иначе None (нет/использован/истёк)."""
    if not token:
        return None
    ev = session.exec(
        select(EmailVerification).where(EmailVerification.token == token)
    ).first()
    if not ev or ev.purpose != purpose:
        return None
    if ev.used_at is not None:
        return None
    if ev.expires_at < datetime.utcnow():
        return None
    user = session.get(User, ev.user_id)
    if not user:
        return None
    now = datetime.utcnow()
    ev.used_at = now
    if not user.is_verified:
        user.is_verified = True
        user.verified_at = now
    session.add(ev)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
