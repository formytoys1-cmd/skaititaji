"""PWA: манифест, service worker и офлайн-страница.

Манифест и service worker обслуживаются с корня, чтобы scope SW был '/'
(иначе он не смог бы контролировать все страницы). Отдаём с корректными
MIME-типами и заголовками кэширования.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import settings
from app.web import render

router = APIRouter()

# Версия кэша: меняйте при обновлении списка кэшируемых ресурсов.
CACHE_VERSION = "skaititaji-v1"


@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> JSONResponse:
    data = {
        "name": settings.app_name,
        "short_name": settings.app_name,
        "description": settings.app_tagline,
        "id": "/?source=pwa",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "orientation": "portrait-primary",
        "background_color": "#f8fafc",
        "theme_color": "#0369a1",
        "lang": settings.default_locale,
        "dir": "ltr",
        "categories": ["utilities", "productivity", "business"],
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192",
             "type": "image/png", "purpose": "any"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "any"},
            {"src": "/static/icons/icon-maskable-192.png", "sizes": "192x192",
             "type": "image/png", "purpose": "maskable"},
            {"src": "/static/icons/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Mans dzīvoklis", "url": "/dzivoklis",
             "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]},
            {"name": "Palīdzība", "url": "/palidziba",
             "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192"}]},
        ],
        "screenshots": [
            {"src": "/static/screenshots/mobile-resident.png", "sizes": "780x1688",
             "type": "image/png", "form_factor": "narrow",
             "label": "Skaitītāju rādījumu nodošana"},
            {"src": "/static/screenshots/desktop-manager.png", "sizes": "1280x800",
             "type": "image/png", "form_factor": "wide",
             "label": "Apsaimniekotāja panelis"},
        ],
    }
    return JSONResponse(
        data,
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# Service worker: app-shell + offline fallback. Сетевые запросы навигации —
# network-first с откатом на /offline; статика — stale-while-revalidate.
_SERVICE_WORKER = """
const CACHE = '%(cache)s';
const OFFLINE_URL = '/offline';
const PRECACHE = [
  '/offline',
  '/static/favicon.svg',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Навигация (HTML): network-first, офлайн -> /offline
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Статика: stale-while-revalidate
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.open(CACHE).then((cache) =>
        cache.match(req).then((cached) => {
          const network = fetch(req).then((res) => {
            if (res && res.status === 200) cache.put(req, res.clone());
            return res;
          }).catch(() => cached);
          return cached || network;
        })
      )
    );
  }
});
""".strip()


@router.get("/sw.js", include_in_schema=False)
def service_worker() -> PlainTextResponse:
    body = _SERVICE_WORKER % {"cache": CACHE_VERSION}
    return PlainTextResponse(
        body,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache",          # SW всегда свежий
            "Service-Worker-Allowed": "/",
        },
    )


@router.get("/offline", include_in_schema=False)
def offline(request: Request):
    return render(request, "offline.html", {})
