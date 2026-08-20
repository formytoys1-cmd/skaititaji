"""Страница «Поделиться»: QR-коды на сайт и установку приложения.

QR генерируются на лету через segno (чистый Python) и отдаются как самостоятельные
SVG-эндпоинты (удобно печатать/встраивать) и встраиваются inline на странице.
Публичная страница /koplietosana — чтобы легко передавать доступ жителям.
"""
from __future__ import annotations

import io

import segno
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.web import render

router = APIRouter()


def _base_url(request: Request) -> str:
    # За прокси Render корректный внешний адрес — из заголовков.
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") \
        or request.url.netloc
    return f"{proto}://{host}"


def _qr_svg(data: str, scale: int = 8, border: int = 2, dark: str = "#0369a1") -> str:
    """Возвращает inline-SVG QR-кода (без XML-декларации, для вставки в HTML)."""
    qr = segno.make(data, error="m")
    buf = io.BytesIO()
    qr.save(
        buf, kind="svg", scale=scale, border=border, dark=dark,
        xmldecl=False, svgns=True, omitsize=False,
    )
    return buf.getvalue().decode("utf-8")


# Целевые ссылки QR-кодов
def _targets(request: Request) -> dict[str, str]:
    base = _base_url(request)
    return {
        "site": base + "/",
        "app": base + "/koplietosana#instalet",  # страница с инструкцией установки
        "help": base + "/palidziba",
    }


@router.get("/qr/{name}.svg", include_in_schema=False)
def qr_svg(name: str, request: Request) -> Response:
    targets = _targets(request)
    if name not in targets:
        return Response(status_code=404)
    svg = _qr_svg(targets[name], scale=10, border=2)
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/koplietosana", include_in_schema=False)
def share_page(request: Request):
    targets = _targets(request)
    qrs = {
        "site": _qr_svg(targets["site"], scale=6, border=2),
        "app": _qr_svg(targets["app"], scale=6, border=2),
    }
    return render(
        request, "share.html",
        {"targets": targets, "qrs": qrs, "base_url": _base_url(request)},
    )
