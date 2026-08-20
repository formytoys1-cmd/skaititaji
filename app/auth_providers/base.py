"""Базовый интерфейс провайдера аутентификации (AUTH-001).

Каждый способ входа (локальный пароль, eIDAS: банк / Smart-ID / eParaksts)
реализует один и тот же интерфейс:

- ``start()`` — инициирует аутентификацию (для eIDAS создаёт сессию у
  провайдера и возвращает данные, нужные для продолжения: код проверки,
  идентификатор сессии). Для локального входа шаг тривиален.
- ``callback()`` — завершает аутентификацию, проверяет результат у провайдера
  и возвращает **верифицированную личность** (:class:`VerifiedIdentity`), либо
  бросает :class:`AuthError` при отказе/отмене/неверной подписи.

Верифицированная личность отвязана от таблицы User: маппинг на пользователя
делает :func:`resolve_user` (ищет по внешнему субъекту, затем по email).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlmodel import Session, select

from app.models import User


class AuthError(Exception):
    """Аутентификация не удалась (отказ, отмена, неверная подпись, таймаут).

    ``reason`` — машиночитаемая причина (``rejected`` | ``cancelled`` |
    ``invalid_signature`` | ``timeout`` | ``error``), ``message`` — текст.
    """

    def __init__(self, reason: str, message: str = "") -> None:
        self.reason = reason
        self.message = message or reason
        super().__init__(self.message)


@dataclass
class VerifiedIdentity:
    """Личность, подтверждённая провайдером аутентификации.

    ``subject`` — стабильный идентификатор личности у провайдера. Для eIDAS это
    национальный персональный код (например ``PNOLV-321...``).
    """

    provider: str
    subject: str
    full_name: str = ""
    email: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthResult:
    """Результат шага ``start()``.

    ``session_id`` — идентификатор сессии у провайдера (нужен для ``callback``).
    ``verification_code`` — код, который пользователь сверяет в приложении
    (Smart-ID). ``challenge`` — прочие данные, нужные фронтенду.
    """

    provider: str
    session_id: str
    verification_code: str = ""
    challenge: dict[str, Any] = field(default_factory=dict)


class AuthProvider(ABC):
    """Базовый интерфейс подключаемого провайдера аутентификации."""

    provider_code: str = "base"

    @abstractmethod
    def start(self, **params: Any) -> AuthResult:
        """Инициировать аутентификацию, вернуть данные для продолжения."""

    @abstractmethod
    def callback(self, **params: Any) -> VerifiedIdentity:
        """Завершить аутентификацию. Вернуть личность или бросить AuthError."""


def resolve_user(session: Session, identity: VerifiedIdentity) -> Optional[User]:
    """Найти пользователя по верифицированной личности.

    Поиск: сперва по паре (external_provider, external_subject); затем по email
    (первый вход через eIDAS для уже существующего локального аккаунта — тогда
    внешний субъект привязывается к нему). Возвращает None, если совпадений нет
    (регистрацию нового аккаунта решает вызывающий код).
    """
    user = session.exec(
        select(User).where(
            User.external_provider == identity.provider,
            User.external_subject == identity.subject,
        )
    ).first()
    if user:
        return user

    if identity.email:
        user = session.exec(
            select(User).where(User.email == identity.email.lower().strip())
        ).first()
        if user:
            # Привязываем внешний субъект к существующему аккаунту.
            if not user.external_subject:
                user.external_provider = identity.provider
                user.external_subject = identity.subject
                session.add(user)
            return user
    return None
