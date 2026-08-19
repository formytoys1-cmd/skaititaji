"""Публичные страницы: лендинг, демо-вход, страница организации."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import MeterType, Organization, User
from app.web import render

router = APIRouter()


@router.get("/")
def landing(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    meter_types = session.exec(
        select(MeterType).where(MeterType.is_active == True)  # noqa: E712
        .order_by(MeterType.sort_order)
    ).all()
    return render(
        request, "public/landing.html",
        {"meter_types": meter_types},
        current_user=current_user,
    )


@router.get("/demo")
def demo(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    org = session.exec(
        select(Organization).where(Organization.slug == "demo-nams")
    ).first()
    return render(
        request, "public/demo.html", {"demo_org": org},
        current_user=current_user, org=org,
    )
