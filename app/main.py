"""Точка входа FastAPI-приложения «Skaitītāji»."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import get_session, init_db
from app.models import MeterType, Organization
from app.routers import admin, auth, manager, moderator, public, resident
from app.seed import seed_demo


async def _self_ping_loop() -> None:
    """Keep-alive: пока приложение живо, периодически запрашивает свой публичный
    URL, чтобы бесплатный инстанс Render не «засыпал» от простоя.

    Работает только в проде (когда задан RENDER_EXTERNAL_URL или SELF_PING_URL).
    Локально ничего не делает.
    """
    base = os.getenv("SELF_PING_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if not base:
        return
    url = base.rstrip("/") + "/api/health"
    interval = int(os.getenv("SELF_PING_INTERVAL", "600"))  # 10 минут
    # первая пауза, чтобы не пинговать во время старта
    await asyncio.sleep(interval)
    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            try:
                await client.get(url)
            except Exception:
                pass
            await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo()  # идемпотентно: создаёт демо-данные, если их ещё нет
    ping_task = asyncio.create_task(_self_ping_loop())
    try:
        yield
    finally:
        ping_task.cancel()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, max_age=60 * 60 * 8)

# Гарантируем наличие каталога статики (пустые папки git не хранит — на свежем
# клоне их может не быть). Без этого StaticFiles упал бы при старте.
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(resident.router)
app.include_router(manager.router)
app.include_router(admin.router)
app.include_router(moderator.router)


# --------------------------------------------------------------------------- #
# Открытый JSON API (для интеграций) — конкурентное преимущество из анализа рынка
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def api_health():
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}


@app.get("/api/meter-types")
def api_meter_types(session: Session = Depends(get_session)):
    types = session.exec(
        select(MeterType).where(MeterType.is_active == True)  # noqa: E712
        .order_by(MeterType.sort_order)
    ).all()
    return [
        {
            "code": t.code, "category": t.category.value,
            "name": {"lv": t.name_lv, "ru": t.name_ru, "en": t.name_en},
            "unit": t.unit, "decimals": t.decimals, "icon": t.icon,
        }
        for t in types
    ]


@app.get("/api/organizations")
def api_organizations(session: Session = Depends(get_session)):
    orgs = session.exec(select(Organization).where(Organization.is_active == True)).all()  # noqa: E712
    return [
        {"slug": o.slug, "name": o.name, "kind": o.kind,
         "integration": o.integration_provider}
        for o in orgs
    ]
