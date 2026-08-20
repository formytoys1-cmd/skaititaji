"""GDPR-001 — процедуры хранения, экспорта и удаления персональных данных.

Реализует права субъекта данных (жителя) по GDPR:
- **Экспорт (ст. 15/20)** — `export_subject_data` собирает все персональные данные
  субъекта (учётка, привязки к квартирам, поданные показания) в структурированном,
  машиночитаемом виде.
- **Удаление/анонимизация (ст. 17)** — `erase_subject` удаляет учётку субъекта и его
  связи с квартирами, но обезличивает (а не удаляет) показания счётчиков: они нужны
  для расчётов и учёта (законный интерес управляющего и требования бухучёта),
  поэтому `submitted_by_id` обнуляется, а сами показания сохраняются.

Мультиарендность и роли:
- субъект может запросить только СВОИ данные;
- управляющий (`MANAGER`) — по субъектам своего арендатора (та же организация) при
  наличии законного основания; проверка выполняется в роутере через `authorize_*`.

Политика ретенции описана в docs/COMPLIANCE_PERSONAL_DATA.md.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.models import Reading, UnitResident, User, UserRole


class GdprAccessError(Exception):
    """Запрос данных субъекта без законного основания/прав."""


def authorize_subject_access(requester: User, subject: User) -> None:
    """Проверяет право `requester` работать с данными субъекта `subject`.

    - Субъект вправе получить только свои данные.
    - Управляющий/суперадмин — только по субъектам своей организации.
    """
    if requester.id == subject.id:
        return
    if requester.role in (UserRole.MANAGER, UserRole.SUPERADMIN):
        if requester.role == UserRole.SUPERADMIN:
            return
        if (
            subject.organization_id is not None
            and subject.organization_id == requester.organization_id
        ):
            return
    raise GdprAccessError("Nav tiesību piekļūt šī subjekta datiem.")


def _subject_or_error(session: Session, subject_id: int) -> User:
    subject = session.get(User, subject_id)
    if subject is None:
        raise GdprAccessError("Subjekts nav atrasts.")
    return subject


def export_subject_data(session: Session, subject_id: int) -> dict:
    """Все персональные данные субъекта в структурированном виде (ст. 15/20)."""
    subject = _subject_or_error(session, subject_id)

    links = session.exec(
        select(UnitResident).where(UnitResident.user_id == subject_id)
    ).all()
    readings = session.exec(
        select(Reading).where(Reading.submitted_by_id == subject_id)
    ).all()

    return {
        "subject": {
            "id": subject.id,
            "email": subject.email,
            "full_name": subject.full_name,
            "phone": subject.phone,
            "locale": subject.locale,
            "role": subject.role.value,
            "organization_id": subject.organization_id,
            "created_at": subject.created_at.isoformat(),
        },
        "units": [
            {"unit_id": link.unit_id, "relation": link.relation}
            for link in links
        ],
        "readings": [
            {
                "id": r.id,
                "meter_id": r.meter_id,
                "period": r.period,
                "value": r.value,
                "consumption": r.consumption,
                "reading_date": r.reading_date.isoformat(),
                "source": r.source.value,
                "status": r.status.value,
                "note": r.note,
            }
            for r in readings
        ],
    }


def erase_subject(session: Session, subject_id: int) -> dict:
    """Удаляет/анонимизирует персональные данные субъекта каскадом (ст. 17).

    Возвращает сводку о выполненном обезличивании (для журнала).
    """
    subject = _subject_or_error(session, subject_id)

    # Обезличиваем показания: сохраняем данные учёта, убираем привязку к субъекту.
    readings = session.exec(
        select(Reading).where(Reading.submitted_by_id == subject_id)
    ).all()
    for r in readings:
        r.submitted_by_id = None
        session.add(r)

    # Каскадно удаляем связи с квартирами.
    links = session.exec(
        select(UnitResident).where(UnitResident.user_id == subject_id)
    ).all()
    for link in links:
        session.delete(link)

    session.delete(subject)
    session.commit()

    return {
        "subject_id": subject_id,
        "anonymized_readings": len(readings),
        "removed_unit_links": len(links),
    }
