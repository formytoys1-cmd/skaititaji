"""Публичные страницы: лендинг, демо-вход, помощь/мануалы."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.help_content import GUIDES, guide_localized
from app.models import MeterType, Organization, User
from app.web import current_lang, render

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


# --------------------------------------------------------------------------- #
# Помощь / мануалы с картинками
# --------------------------------------------------------------------------- #
_GUIDES = {
    "iedzivotajs": "resident",
    "apsaimniekotajs": "manager",
    "administrators": "admin",
}
_GUIDE_SLUG = {v: k for k, v in _GUIDES.items()}


@router.get("/palidziba")
def help_index(
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    lang = current_lang(request)
    cards = []
    for key, g in GUIDES.items():
        cards.append({
            "slug": _GUIDE_SLUG[key],
            "icon": g["icon"],
            "title": g["title"].get(lang, g["title"]["lv"]),
        })
    return render(request, "help/index.html", {"cards": cards},
                  current_user=current_user)


@router.get("/palidziba/{guide}")
def help_guide(
    guide: str,
    request: Request,
    current_user: User | None = Depends(get_current_user),
):
    if guide not in _GUIDES:
        return RedirectResponse("/palidziba", 303)
    lang = current_lang(request)
    data = guide_localized(_GUIDES[guide], lang)
    return render(
        request, "help/guide.html", {"guide": data},
        current_user=current_user,
    )
