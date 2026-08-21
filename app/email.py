"""Отправка e-mail (подтверждение адреса при самрегистрации).

Free-режим по умолчанию: если SMTP не настроен (`EMAIL_HOST` пуст), письма не
уходят наружу, а сохраняются в `data/outbox/` и логируются — этого достаточно
для демо и тестов, без внешних платных сервисов. В проде задаются переменные
`EMAIL_HOST/PORT/USER/PASSWORD/FROM` (подойдёт бесплатный SMTP, напр. Gmail с
app-password), и письма уходят по-настоящему.

Секреты берутся только из окружения и никогда не попадают в репозиторий.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from app.config import settings

logger = logging.getLogger("skaititaji.email")

_OUTBOX = Path("data/outbox")


def _write_outbox(to: str, subject: str, body: str) -> Path:
    """Фоллбек без SMTP: сохранить письмо на диск и залогировать."""
    _OUTBOX.mkdir(parents=True, exist_ok=True)
    safe = to.replace("@", "_at_").replace("/", "_")
    ts = __import__("time").strftime("%Y%m%d-%H%M%S")
    path = _OUTBOX / f"{ts}_{safe}.txt"
    path.write_text(
        f"To: {to}\nFrom: {settings.email_from}\nSubject: {subject}\n\n{body}\n",
        encoding="utf-8",
    )
    logger.info("email(outbox) -> %s | %s | file=%s", to, subject, path)
    return path


def send_email(to: str, subject: str, body: str) -> bool:
    """Отправляет письмо. Возвращает True, если доставлено (или записано в
    outbox в free-режиме). Никогда не бросает наружу — при ошибке SMTP
    откатывается в outbox, чтобы поток регистрации не падал."""
    if not settings.email_configured:
        _write_outbox(to, subject, body)
        return True
    try:
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(settings.email_host, settings.email_port, timeout=20) as s:
            if settings.email_use_tls:
                s.starttls(context=ssl.create_default_context())
            if settings.email_user:
                s.login(settings.email_user, settings.email_password)
            s.send_message(msg)
        logger.info("email(smtp) -> %s | %s", to, subject)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("SMTP failed (%s); fallback to outbox", e)
        _write_outbox(to, subject, body)
        return True


def verification_email(full_name: str, link: str, app_name: str) -> tuple[str, str]:
    """Стандартный текст письма подтверждения. Возвращает (subject, body)."""
    subject = f"{app_name}: apstipriniet savu e-pastu / подтвердите e-mail"
    body = (
        f"Sveiki, {full_name}!\n\n"
        f"Jūs reģistrējāties portālā {app_name} skaitītāju rādījumu nodošanai.\n"
        f"Lai pabeigtu reģistrāciju, apstipriniet savu e-pasta adresi:\n\n"
        f"    {link}\n\n"
        f"Saite ir derīga 24 stundas. Ja jūs neveicāt reģistrāciju, "
        f"vienkārši ignorējiet šo vēstuli.\n\n"
        f"— — —\n\n"
        f"Здравствуйте, {full_name}!\n\n"
        f"Вы зарегистрировались на портале {app_name} для подачи показаний "
        f"счётчиков. Чтобы завершить регистрацию, подтвердите свой e-mail:\n\n"
        f"    {link}\n\n"
        f"Ссылка действительна 24 часа. Если вы не регистрировались — "
        f"просто проигнорируйте это письмо.\n\n"
        f"{app_name}"
    )
    return subject, body
