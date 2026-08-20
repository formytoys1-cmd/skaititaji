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
from app.routers import (
    admin,
    agent_api,
    auth,
    management,
    manager,
    moderator,
    public,
    pwa,
    resident,
    share,
)
from app.seed import ensure_demo_extras, seed_demo


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
    ensure_demo_extras()  # точечные доводчики к уже существующей БД
    ping_task = asyncio.create_task(_self_ping_loop())
    try:
        yield
    finally:
        ping_task.cancel()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


# --------------------------------------------------------------------------- #
# Security headers (OWASP secure headers project, MDN best practices)
# --------------------------------------------------------------------------- #
# CSP разрешает Tailwind CDN и axe (cdnjs) — источники, которые реально нужны.
# 'unsafe-inline' для скриптов пока необходим из-за встроенных <script> и
# Tailwind-CDN рантайма; см. дорожную карту (прод-сборка Tailwind → строгий CSP).
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "worker-src 'self'; "
    "manifest-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = _CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    )
    # HSTS включаем только на HTTPS (за прокси Render заголовок x-forwarded-proto).
    if request.headers.get("x-forwarded-proto", request.url.scheme) == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    return response


# Сессионная cookie: HttpOnly (по умолчанию), Secure в проде, SameSite=Lax.
# Прод определяется явными сигналами (settings.is_production), а не DEBUG —
# иначе локальное демо (DEBUG по умолчанию 0, SEC-002) требовало бы HTTPS.
_is_prod = settings.is_production
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=_is_prod,
)

# Гарантируем наличие каталога статики (пустые папки git не хранит — на свежем
# клоне их может не быть). Без этого StaticFiles упал бы при старте.
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(resident.router)
app.include_router(manager.router)
app.include_router(management.router)
app.include_router(admin.router)
app.include_router(moderator.router)
app.include_router(agent_api.router)
app.include_router(pwa.router)
app.include_router(share.router)


# Кастомная 404-страница (брендированная, 3 языка).
from app.database import engine as _engine  # noqa: E402
from app.models import User as _User  # noqa: E402
from app.web import render as _render  # noqa: E402


@app.exception_handler(404)
async def not_found_handler(request, exc):
    if request.url.path.startswith("/api/"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Not found"}, status_code=404)
    user = None
    try:
        uid = request.session.get("user_id") if hasattr(request, "session") else None
        if uid:
            with Session(_engine) as s:
                user = s.get(_User, uid)
    except Exception:
        user = None
    return _render(request, "404.html", current_user=user, status_code=404)


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
