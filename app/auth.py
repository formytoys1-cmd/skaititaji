"""Аутентификация и авторизация (упрощённая, для демо).

Пароли хэшируются PBKDF2 из стандартной библиотеки — без внешних зависимостей.
Сессия хранится в подписанной cookie (Starlette SessionMiddleware).

В продакшене здесь ожидается вход через банк / Smart-ID / eParaksts (eIDAS),
как это принято в латвийских порталах — см. docs/TZ.md.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, UserRole

_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def login_user(request: Request, user: User) -> None:
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value


def logout_user(request: Request) -> None:
    request.session.clear()


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return session.get(User, user_id)


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Nav autorizēts"
        )
    return user


def require_role(*roles: UserRole):
    def checker(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Nav piekļuves"
            )
        return user

    return checker


def authenticate(session: Session, email: str, password: str) -> Optional[User]:
    user = session.exec(
        select(User).where(User.email == email.lower().strip())
    ).first()
    if user and user.is_active and verify_password(password, user.password_hash):
        return user
    return None
