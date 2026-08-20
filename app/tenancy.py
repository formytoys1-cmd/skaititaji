"""SEC-008 — Централизованная проверка принадлежности сущности арендатору.

Мультиарендность построена на модели Organization. Любой доступ к сущности по
прямому id из URL/формы обязан проходить проверку принадлежности организации
текущего пользователя, иначе возможен IDOR (чтение/изменение чужих данных по
подставленному id).

Ранее такие проверки были размазаны по роутерам ad-hoc хелперами. Здесь они
собраны в одном аудируемом месте: `owned_*` возвращает сущность ТОЛЬКО если она
принадлежит организации, иначе `None`. HTML-роутеры превращают `None` в «не
найдено» (редирект), API — в 404.
"""
from __future__ import annotations

from sqlmodel import Session

from app.models import Building, Meter, Organization, Unit


def owned_building(
    session: Session, org: Organization, building_id: int
) -> Building | None:
    """Дом, принадлежащий организации, либо None (чужой/несуществующий)."""
    b = session.get(Building, building_id)
    if b is not None and b.organization_id == org.id:
        return b
    return None


def owned_unit(session: Session, org: Organization, unit_id: int) -> Unit | None:
    """Квартира, принадлежащая организации через свой дом, либо None."""
    u = session.get(Unit, unit_id)
    if u is None:
        return None
    if owned_building(session, org, u.building_id) is not None:
        return u
    return None


def owned_meter(session: Session, org: Organization, meter_id: int) -> Meter | None:
    """Счётчик, принадлежащий организации через квартиру и дом, либо None."""
    m = session.get(Meter, meter_id)
    if m is None:
        return None
    if owned_unit(session, org, m.unit_id) is not None:
        return m
    return None
