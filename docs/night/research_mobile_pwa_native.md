
[Turn 0]
Теперь у меня достаточно контекста о реальной кодовой базе. Формирую полный отчёт.

---

# 📱 Мобилизация веб-приложения «Skaitītāji» — Практический отчёт 2024–2026

> Стек: Python FastAPI + Jinja2 + Tailwind CDN · Render · Роли: resident/manager/superadmin · i18n: LV/RU/EN · WCAG 2.2 AA

---

## Содержание

1. [Сравнение путей — TL;DR](#сравнение)
2. [ПУТЬ 1 — PWA](#pwa)
   - [Манифест](#manifest)
   - [Иконки](#icons)
   - [Service Worker](#sw)
   - [iOS-специфика](#ios)
   - [Кнопка «Установить»](#install-button)
   - [FastAPI: раздача файлов](#fastapi-serving)
   - [CSP — критический нюанс](#csp)
   - [Lighthouse PWA чек-лист](#lighthouse)
3. [ПУТЬ 2 — Expo / React Native](#expo)
   - [Вариант A: WebView-обёртка](#webview)
   - [Вариант B: нативные экраны + JSON API](#native)
   - [Структура проекта](#expo-structure)
   - [EAS Build и публикация](#eas)
4. [Реалистичная оценка усилий](#effort)
5. [Roadmap](#roadmap)
6. [Источники](#sources)

---

## Сравнение путей {#сравнение}

| Критерий | PWA | Expo/RN WebView | Expo/RN Нативный |
|---|---|---|---|
| **Усилия** | 1–2 дня | 3–5 дней | 4–8 недель |
| **App Store** | ❌ нет | ✅ да | ✅ да |
| **Google Play** | ❌ нет (TWA — можно) | ✅ да | ✅ да |
| **Обновления** | Мгновенно через деплой | WebView — мгновенно; нативный — через EAS Update | Через EAS Update (OTA) |
| **Push-уведомления** | iOS 16.4+ после A2HS | Полноценные | Полноценные |
| **WCAG 2.2 AA** | Уже готово | Нужна адаптация | Нужна адаптация |
| **Стоимость** | $0 | $99/год (Apple) + $25 (Google) | То же |
| **Рекомендация** | **Начать здесь** | Шаг 2, если нужен Store | Шаг 3, долгосрочно |

---

## ПУТЬ 1 — PWA {#pwa}

### 1.1 Манифест `app.webmanifest` {#manifest}

Создайте файл `app/static/app.webmanifest`:

```json
{
  "name": "Skaitītāji — Komunālie pakalpojumi",
  "short_name": "Skaitītāji",
  "description": "Iesniegt skaitītāju rādījumus / Подача показаний счётчиков",
  "id": "/?source=pwa",
  "start_url": "/?source=pwa",
  "scope": "/",
  "display": "standalone",
  "display_override": ["standalone", "minimal-ui"],
  "orientation": "portrait-primary",
  "lang": "lv",
  "dir": "ltr",
  "theme_color": "#0369a1",
  "background_color": "#f8fafc",
  "categories": ["utilities", "productivity"],
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/static/icons/icon-maskable-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/static/screenshots/mobile-resident.png",
      "sizes": "390x844",
      "type": "image/png",
      "form_factor": "narrow",
      "label": "Рабочий кабинет жителя"
    },
    {
      "src": "/static/screenshots/desktop-manager.png",
      "sizes": "1280x800",
      "type": "image/png",
      "form_factor": "wide",
      "label": "Панель управляющего"
    }
  ],
  "shortcuts": [
    {
      "name": "Iesniegt rādījumus",
      "short_name": "Rādījumi",
      "url": "/dzivoklis?source=pwa-shortcut",
      "icons": [{ "src": "/static/icons/shortcut-meter.png", "sizes": "96x96" }]
    }
  ],
  "prefer_related_applications": false
}
```

**Ключевые пояснения:**
- `"id"` — фиксирует идентификатор PWA независимо от `start_url`; важно для будущих рефакторингов URL. ([web.dev/articles/add-manifest](https://web.dev/articles/add-manifest))
- `"display": "standalone"` — убирает адресную строку; `display_override` для браузеров, поддерживающих `minimal-ui` как фолбек.
- `"screenshots"` с `form_factor` — требование Chrome с 2023 года для показа расширённого диалога установки («rich install UI»).
- `"categories"` — используется в каталогах и поиске.
- Многоязычность манифеста: у Google нет стандарта для мультиязычного манифеста — отдавайте манифест через FastAPI-эндпоинт и динамически подставляйте `name`/`description` по `Accept-Language` или сессионному языку пользователя (см. ниже).

---

### 1.2 Иконки {#icons}

#### Требуемые файлы

```
app/static/icons/
├── icon-192.png          # 192×192, PNG, purpose: any
├── icon-512.png          # 512×512, PNG, purpose: any
├── icon-maskable-512.png # 512×512, PNG, purpose: maskable (safe zone ≥ 80% центра)
├── apple-touch-icon.png  # 180×180, PNG (iOS «Add to Home Screen»)
└── shortcut-meter.png    # 96×96, PNG (ярлык быстрого доступа)
```

#### Правила maskable-иконки

- Весь смысловой контент (логотип 💧, текст) — **внутри центрального круга радиусом 40% от ширины** (safe zone).
- Внешние 10% края **могут быть обрезаны**.
- Фон должен быть **непрозрачным** (цвет бренда `#0369a1` или нейтральный).
- Инструмент проверки: [maskable.app](https://maskable.app/) (бесплатно).
- В DevTools → Application → Icons → ✓ «Show only the minimum safe area for maskable icons».

> **⚠️ Не ставьте `"purpose": "any maskable"` в одной записи** — Chrome правильно обрабатывает, но Safari/iOS игнорирует, и ваш логотип окажется с белым фоном на Android. Используйте **два отдельных объекта** с разными `purpose`. ([web.dev/articles/maskable-icon](https://web.dev/articles/maskable-icon))

#### iOS apple-touch-icon

iOS не использует `manifest.icons` для иконки на домашнем экране. Она берёт иконку **только из `<link>` тегов в `<head>` HTML** или ищет `/apple-touch-icon.png` в корне сайта автоматически.

Добавьте в `app/templates/base.html` (внутри `<head>`, после существующих `<link>`):

```html
<!-- PWA Manifest -->
<link rel="manifest" href="/app.webmanifest">

<!-- iOS Home Screen Icon (Safari берёт именно отсюда) -->
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">

<!-- iOS статус-бар и полноэкранный режим -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Skaitītāji">

<!-- Android/Chrome theme (уже есть color-scheme, добавляем theme-color) -->
<meta name="theme-color" content="#0369a1">

<!-- Регистрация Service Worker -->
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js', { scope: '/' })
        .then(reg => console.log('SW registered, scope:', reg.scope))
        .catch(err => console.error('SW registration failed:', err));
    });
  }
</script>
```

#### iOS Splash Screen (Startup Image)

iOS генерирует splash из иконки + `background_color` манифеста **автоматически начиная с iOS 12+**, но кастомный splash задаётся через `<link rel="apple-touch-startup-image">`. Поскольку устройств много (от iPhone SE до Pro Max), рекомендуем **не делать** статические спалши вручную — слишком много размеров. Вместо этого полагайтесь на автоматический генератор или используйте скрипт (например, [pwa-asset-generator](https://github.com/elegantapp/pwa-asset-generator)).

---

### 1.3 Service Worker `/sw.js` {#sw}

Разместите в `app/static/sw.js` — **но** отдавайте его с корневого пути `/sw.js` через FastAPI (см. раздел 1.5), иначе scope будет `/static/`, а не `/`.

```javascript
// sw.js — App Shell + Offline Fallback Strategy
// Версия кэша — меняйте при каждом деплое (или генерируйте автоматически)
const CACHE_NAME = 'skaititaji-shell-v1';
const OFFLINE_URL = '/offline';

// App Shell: минимальный набор ресурсов для работы без сети
const SHELL_ASSETS = [
  '/',
  '/offline',
  '/static/css/main.css',          // если есть собственный CSS
  '/static/icons/icon-192.png',
  '/static/icons/apple-touch-icon.png',
  // НЕ кэшируем Tailwind CDN — он внешний и нестабилен offline
];

// ── INSTALL ───────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting()) // ← активируем SW сразу, не ждём закрытия вкладок
  );
});

// ── ACTIVATE ──────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(key => key !== CACHE_NAME) // удаляем старые версии кэша
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim()) // ← берём контроль над всеми открытыми вкладками
  );
});

// ── FETCH ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Пропускаем: не-GET, cross-origin, API-запросы, админ-роуты
  if (
    request.method !== 'GET' ||
    url.origin !== location.origin ||
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/admin') ||
    request.headers.get('Accept')?.includes('application/json')
  ) {
    return; // браузер обрабатывает сам, без SW
  }

  // Стратегия: Network First → Cache Fallback → Offline Page
  // Подходит для динамических Jinja2-страниц (всегда свежие данные)
  event.respondWith(
    fetch(request)
      .then(response => {
        // Кэшируем успешные GET-ответы страниц (не POST/redirect)
        if (response.ok && response.status === 200) {
          const clone = response.clone();
          // Кэшируем только shell-ресурсы, не все страницы
          if (SHELL_ASSETS.includes(url.pathname)) {
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
        }
        return response;
      })
      .catch(() => {
        // Нет сети → пробуем кэш
        return caches.match(request)
          .then(cached => cached || caches.match(OFFLINE_URL));
      })
  );
});
```

#### Стратегии кэширования — когда что применять

| Стратегия | Применение в вашем проекте |
|---|---|
| **Cache First** | Статика: иконки, шрифты, CSS-файлы |
| **Network First** | Все Jinja2-страницы (данные всегда актуальные) |
| **Stale-While-Revalidate** | Tailwind CDN — **не применять**, т.к. CDN внешний и CSP его ограничивает |
| **Network Only** | POST-запросы форм, `/api/*`, `/admin/*` |
| **Cache Only + Offline Fallback** | Страница `/offline` — всегда из кэша |

#### `skipWaiting` + `clients.claim` — зачем

- `skipWaiting()` в `install` — новый SW активируется **немедленно**, не ожидая закрытия всех вкладок с предыдущей версией.
- `clients.claim()` в `activate` — SW берёт под контроль уже открытые вкладки без перезагрузки.
- **Подводный камень**: если в момент `clients.claim()` на вкладке идёт транзакция или навигация, поведение может быть непредсказуемым. Для production рекомендуется показывать уведомление «Обновление доступно — перезагрузите страницу» вместо автоматического `skipWaiting`. ([web.dev/articles/service-worker-lifecycle](https://web.dev/articles/service-worker-lifecycle))

#### Страница `/offline`

Создайте `app/templates/offline.html` с минимальным шаблоном (без Tailwind CDN — он не загрузится offline):

```html
<!DOCTYPE html>
<html lang="lv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nav savienojuma — Skaitītāji</title>
  <style>
    body { font-family: -apple-system, sans-serif; display: flex; flex-direction: column;
           align-items: center; justify-content: center; min-height: 100vh;
           background: #f8fafc; color: #1e293b; margin: 0; padding: 1rem; text-align: center; }
    h1 { font-size: 1.5rem; margin-bottom: .5rem; }
    p { color: #64748b; margin-bottom: 1.5rem; }
    button { background: #0369a1; color: white; border: none; padding: .75rem 1.5rem;
             border-radius: .5rem; font-size: 1rem; cursor: pointer; }
  </style>
</head>
<body>
  <span style="font-size:3rem" aria-hidden="true">📶</span>
  <h1>Nav interneta savienojuma</h1>
  <p>Нет подключения к интернету · No internet connection</p>
  <button onclick="location.reload()">Mēģināt vēlreiz / Повторить</button>
</body>
</html>
```

---

### 1.4 iOS-специфика {#ios}

#### Ограничения PWA на iOS (актуально 2024–2026)

| Функция | Статус iOS |
|---|---|
| `display: standalone` | ✅ Поддерживается с iOS 11.3 |
| Push Notifications | ✅ iOS **16.4+** — только через Web Push API, **только** если пользователь добавил сайт через «Add to Home Screen». В браузере Safari без A2HS — **нельзя**. |
| Background Sync | ❌ Не поддерживается |
| Service Worker Cache | ✅ Поддерживается (с iOS 11.3) |
| IndexedDB | ✅ Поддерживается |
| Storage Persistence | ⚠️ iOS очищает кэш SW/IndexedDB при нехватке места или если приложение не запускалось >7 дней |
| Clipboard API | ⚠️ Частично |
| Camera / Microphone | ✅ С разрешения пользователя |

#### `apple-mobile-web-app-status-bar-style`

```html
<!-- Варианты: default | black | black-translucent -->
<!-- "default" — белый статус-бар (рекомендуется для светлой темы) -->
<meta name="apple-mobile-web-app-status-bar-style" content="default">
```

- `black-translucent` — статус-бар накладывается поверх контента (контент начинается под часами). Нужен `padding-top: env(safe-area-inset-top)` в CSS.
- Для вашего проекта (`light` color-scheme) — используйте `default`.

#### Safe Area Insets (iPhone с «чёлкой» и Dynamic Island)

```css
/* В base.html <style> — уже стоит sticky header, добавьте: */
header {
  padding-top: env(safe-area-inset-top);
}
body {
  padding-bottom: env(safe-area-inset-bottom); /* нижний «домашний» бар */
}
```

---

### 1.5 Кнопка «Установить» {#install-button}

Поведение различается на Android (Chrome) и iOS (Safari):

```html
<!-- Добавьте в base.html перед </body> -->
<div id="pwaInstallBanner" hidden
     class="fixed bottom-16 inset-x-4 md:right-4 md:left-auto md:max-w-sm z-50
            bg-white border border-slate-200 rounded-xl shadow-xl p-4"
     role="region" aria-label="Installer app">
  <!-- Android/Chrome: автоматический prompt -->
  <div id="androidInstall">
    <p class="text-sm font-semibold text-slate-800 mb-1">📱 Instalēt lietotni</p>
    <p class="text-xs text-slate-600 mb-3">Pievienot sākuma ekrānam / Добавить на главный экран</p>
    <div class="flex gap-2">
      <button id="btnInstall"
              class="flex-1 px-3 py-2 rounded-lg brand-bg text-white text-sm font-semibold">
        Instalēt
      </button>
      <button id="btnInstallDismiss"
              class="px-3 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm">
        Vēlāk
      </button>
    </div>
  </div>
  <!-- iOS Safari: инструкция (beforeinstallprompt не работает) -->
  <div id="iosInstall" hidden>
    <p class="text-sm font-semibold text-slate-800 mb-1">📱 Pievienot sākuma ekrānam</p>
    <p class="text-xs text-slate-600">
      Nospiediet <strong>☐↑</strong> (Kopīgot) → «Pievienot sākuma ekrānam»<br>
      <span class="text-slate-400">Нажмите Поделиться → «На экран Домой»</span>
    </p>
    <button id="btnIosDismiss" class="mt-3 text-xs text-slate-500 underline">Закрыть</button>
  </div>
</div>

<script>
(function () {
  const banner = document.getElementById('pwaInstallBanner');
  const androidDiv = document.getElementById('androidInstall');
  const iosDiv = document.getElementById('iosInstall');

  // Не показываем, если уже установлено (standalone mode)
  if (window.matchMedia('(display-mode: standalone)').matches) return;
  // Не показываем, если уже отклонили
  if (localStorage.getItem('pwaInstallDismissed')) return;

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;

  // Android/Chrome: ловим beforeinstallprompt
  let deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    androidDiv.hidden = false;
    iosDiv.hidden = true;
    banner.hidden = false;
  });

  document.getElementById('btnInstall')?.addEventListener('click', async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    banner.hidden = true;
    if (outcome === 'dismissed') localStorage.setItem('pwaInstallDismissed', '1');
  });

  document.getElementById('btnInstallDismiss')?.addEventListener('click', () => {
    banner.hidden = true;
    localStorage.setItem('pwaInstallDismissed', '1');
  });

  // iOS: beforeinstallprompt не стреляет — показываем инструкцию вручную
  if (isIOS) {
    // Показываем только в Safari (не в Chrome/Firefox на iOS)
    const isSafari = /safari/i.test(navigator.userAgent) && !/chrome|crios|fxios/i.test(navigator.userAgent);
    if (isSafari) {
      androidDiv.hidden = true;
      iosDiv.hidden = false;
      // Показываем с задержкой, чтобы не мешать первой загрузке
      setTimeout(() => { banner.hidden = false; }, 3000);
    }
  }

  document.getElementById('btnIosDismiss')?.addEventListener('click', () => {
    banner.hidden = true;
    localStorage.setItem('pwaInstallDismissed', '1');
  });
})();
</script>
```

---

### 1.6 FastAPI: раздача `manifest` и `sw.js` {#fastapi-serving}

**Критически важно**: Service Worker должен отдаваться **с корневого пути** `/sw.js`, иначе его `scope` будет ограничен `/static/` и он не сможет перехватывать запросы к `/dzivoklis`, `/parvalde` и т.д.

Добавьте в `app/routers/public.py` (или в `main.py`):

```python
import json
from fastapi import Request
from fastapi.responses import FileResponse, Response

# ── PWA: Service Worker с корневым scope ─────────────────────────────────────
@router.get("/sw.js", include_in_schema=False)
async def service_worker():
    """Отдаём SW из /static/sw.js но по пути /sw.js для корректного scope."""
    return FileResponse(
        "app/static/sw.js",
        media_type="application/javascript",
        headers={
            # Service-Worker-Allowed разрешает scope шире расположения файла
            "Service-Worker-Allowed": "/",
            # SW должен обновляться при каждом визите (no-cache)
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )

# ── PWA: Манифест (динамический, с учётом языка сессии) ─────────────────────
@router.get("/app.webmanifest", include_in_schema=False)
async def web_manifest(request: Request):
    lang = request.session.get("lang", "lv")
    names = {
        "lv": ("Skaitītāji — Komunālie pakalpojumi", "Rādījumi"),
        "ru": ("Счётчики — Коммунальные услуги", "Показания"),
        "en": ("Meters — Utility Services", "Readings"),
    }
    name, short = names.get(lang, names["lv"])
    manifest = {
        "name": name,
        "short_name": short,
        "description": "Iesniegt skaitītāju rādījumus",
        "id": "/?source=pwa",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "lang": lang,
        "dir": "ltr",
        "theme_color": "#0369a1",
        "background_color": "#f8fafc",
        "categories": ["utilities", "productivity"],
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/static/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "screenshots": [
            {"src": "/static/screenshots/mobile-resident.png", "sizes": "390x844", "type": "image/png", "form_factor": "narrow"},
        ],
        "shortcuts": [
            {"name": "Iesniegt rādījumus", "short_name": "Rādījumi", "url": "/dzivoklis?source=pwa-shortcut"},
        ],
        "prefer_related_applications": False,
    }
    return Response(
        content=json.dumps(manifest, ensure_ascii=False),
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )

# ── PWA: Offline fallback страница ───────────────────────────────────────────
@router.get("/offline", include_in_schema=False)
async def offline_page(request: Request):
    # render() — ваша утилита из app/web.py
    return render(request, "offline.html")
```

---

### 1.7 CSP — критический нюанс {#csp}

В вашем `main.py` строка CSP:
```python
"connect-src 'self'; "
```

Service Worker использует `fetch()` для network-first запросов — это `connect-src`. Tailwind CDN (`cdn.tailwindcss.com`) нужен в `script-src` и `connect-src`. Текущий CSP это **уже разрешает** для скриптов, но при offline запрос к CDN упадёт. **Решение** — не кэшировать CDN-скрипт в SW (мы так и сделали выше) и убедиться, что offline-страница не зависит от CDN.

Также добавьте в CSP разрешение для manifest (уже работает через `default-src 'self'`).

---

### 1.8 Lighthouse PWA чек-лист {#lighthouse}

Запустите: DevTools → Lighthouse → ✓ Progressive Web App → Generate report

#### Критерии installability (все должны быть ✅)

- [ ] Есть `<link rel="manifest">` в `<head>`
- [ ] Манифест валиден: `name`/`short_name`, `icons` (192 + 512), `start_url`, `display`
- [ ] Service Worker зарегистрирован и активен
- [ ] Сайт обслуживается по **HTTPS** (Render даёт автоматически ✅)
- [ ] `start_url` отвечает при offline (через SW кэш)
- [ ] `theme-color` meta тег в `<head>` совпадает с `theme_color` в манифесте
- [ ] Иконки 192×192 и 512×512 доступны
- [ ] Viewport meta тег присутствует (`width=device-width`) ✅ уже есть

#### Дополнительные критерии (optimal PWA)

- [ ] Maskable icon
- [ ] Offline страница с контентом (не просто HTTP 200)
- [ ] Splash screen (автоматически из manifest + `background_color`)
- [ ] Screenshots в манифесте (для rich install dialog в Chrome)

---

## ПУТЬ 2 — Expo / React Native {#expo}

### 2.1 Вариант A — WebView-обёртка (быстрый путь) {#webview}

**Суть**: берём PWA как есть, оборачиваем в `expo-web-browser` / `react-native-webview`. Это позволяет опубликовать в App Store/Play Store с минимальными усилиями.

**Преимущества**: весь UI и бизнес-логика остаются в вашем Python/Jinja2 стеке.
**Недостатки**: Apple может отклонить приложение, если оно «просто сайт в браузере» без нативной функциональности. На практике — добавьте хотя бы push-уведомления или biometric login.

### 2.2 Вариант B — Нативные экраны + JSON API {#native}

**Суть**: создаём нативное Expo-приложение, которое обращается к вашему FastAPI бэкенду через REST API. Нужно добавить JSON-эндпоинты к существующим роутерам.

### 2.3 Структура Expo-проекта {#expo-structure}

```bash
# Создание проекта (SDK 57, август 2026)
npx create-expo-app@latest SkaititajiMobile --template default@sdk-57
cd SkaititajiMobile
```

#### Структура файлов

```
SkaititajiMobile/
├── app/                          # Expo Router (file-based routing)
│   ├── _layout.tsx               # Root layout (NavigationContainer)
│   ├── index.tsx                 # Главный экран (redirect по роли)
│   ├── (auth)/
│   │   ├── login.tsx             # Экран логина
│   │   └── _layout.tsx
│   ├── (resident)/
│   │   ├── _layout.tsx
│   │   ├── index.tsx             # Дашборд жителя
│   │   └── submit-reading.tsx    # Подача показаний
│   ├── (manager)/
│   │   ├── _layout.tsx
│   │   └── index.tsx             # Панель управляющего
│   └── webview.tsx               # Фолбек: полноэкранный WebView
├── components/
│   ├── ReadingForm.tsx
│   └── MeterCard.tsx
├── services/
│   └── api.ts                    # Клиент к FastAPI
├── hooks/
│   └── useAuth.ts
├── constants/
│   └── Colors.ts                 # brand: '#0369a1'
├── assets/
│   ├── icon.png                  # 1024×1024
│   ├── adaptive-icon.png         # 1024×1024 (Android adaptive)
│   └── splash-icon.png
├── app.json                      # Конфигурация Expo
├── eas.json                      # EAS Build профили
└── package.json
```

#### `app.json` (ключевые поля)

```json
{
  "expo": {
    "name": "Skaitītāji",
    "slug": "skaititaji",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "scheme": "skaititaji",
    "userInterfaceStyle": "light",
    "splash": {
      "image": "./assets/splash-icon.png",
      "resizeMode": "contain",
      "backgroundColor": "#f8fafc"
    },
    "ios": {
      "supportsTablet": false,
      "bundleIdentifier": "com.skaititaji.app",
      "buildNumber": "1",
      "infoPlist": {
        "NSCameraUsageDescription": "Fotografēt skaitītāju rādījumus",
        "NSPhotoLibraryUsageDescription": "Augšupielādēt skaitītāja foto"
      }
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#0369a1"
      },
      "package": "com.skaititaji.app",
      "versionCode": 1,
      "permissions": ["CAMERA", "READ_EXTERNAL_STORAGE"]
    },
    "plugins": [
      "expo-router",
      ["expo-camera", { "cameraPermission": "Foto skaitītājam" }]
    ],
    "experiments": {
      "typedRoutes": true
    }
  }
}
```

#### `eas.json` (EAS Build профили)

```json
{
  "cli": { "version": ">= 16.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": { "buildType": "apk" }
    },
    "production": {
      "autoIncrement": true
    }
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "your@email.com",
        "ascAppId": "XXXXXXXXXX",
        "appleTeamId": "XXXXXXXXXX"
      },
      "android": {
        "serviceAccountKeyPath": "./google-services.json",
        "track": "production"
      }
    }
  }
}
```

#### Минимальный API-клиент `services/api.ts`

```typescript
// services/api.ts
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'https://your-app.onrender.com';

interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: object;
  token?: string;
}

export async function apiFetch<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: opts.method ?? 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(opts.token ? { 'Authorization': `Bearer ${opts.token}` } : {}),
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

#### Что нужно добавить в FastAPI для нативного клиента

Ваши текущие роутеры возвращают HTML (Jinja2). Для мобильного клиента нужны JSON-эндпоинты. Пример паттерна:

```python
# В resident.py — добавьте JSON-версии
from fastapi import APIRouter
from fastapi.responses import JSONResponse

@router.get("/api/v1/resident/readings")
async def api_get_readings(current_user = Depends(get_current_user), db = Depends(get_session)):
    """JSON API для мобильного клиента."""
    readings = db.exec(select(Reading).where(Reading.user_id == current_user.id)).all()
    return {"readings": [r.model_dump() for r in readings]}

@router.post("/api/v1/resident/readings")
async def api_submit_reading(data: ReadingCreate, ...):
    ...
```

---

### 2.4 EAS Build и публикация {#eas}

#### Команды

```bash
# Установка EAS CLI
npm install -g eas-cli

# Логин в Expo
eas login

# Настройка проекта (генерирует app.json дополнения)
eas build:configure

# Development build (тестирование на устройстве)
eas build --profile development --platform ios

# Preview build (внутреннее тестирование, без сертификатов App Store)
eas build --profile preview --platform android

# Production build (готово к публикации)
eas build --profile production --platform all

# Отправка в магазины
eas submit --platform ios    # → TestFlight → App Store Review
eas submit --platform android # → Google Play Internal Track
```

#### Требования к публикации

**Apple App Store** ($99/год, developer.apple.com):
- [ ] Apple Developer Program membership
- [ ] App Store Connect аккаунт
- [ ] Иконка 1024×1024 PNG (без альфа-канала)
- [ ] Минимум 3 скриншота для iPhone 6.5" (1284×2778)
- [ ] Privacy Policy URL (у вас `/privatums` — нужен публичный URL)
- [ ] Privacy Nutrition Labels (какие данные собираете)
- [ ] Описание на английском (обязательно) + LV/RU (опционально)
- [ ] Review Notes (логин для тестирования: используйте демо-аккаунт)
- [ ] Compliance: шифрование (HTTPS → выберите «Yes, uses standard encryption»)

**Google Play** ($25 разово, play.google.com/console):
- [ ] Google Play Developer Account
- [ ] Иконка 512×512 PNG
- [ ] Feature Graphic 1024×500
- [ ] Минимум 2 скриншота телефона
- [ ] Privacy Policy URL
- [ ] Target API level 35+ (Android 15, требование с августа 2025)
- [ ] Data Safety Form

---

## Реалистичная оценка усилий {#effort}

| Этап | Задача | Оценка |
|---|---|---|
| **PWA — день 1** | Иконки (maskable.app), манифест, мета-теги в base.html | 4–6 часов |
| **PWA — день 2** | Service Worker, offline-страница, FastAPI-роуты, тест Lighthouse | 6–8 часов |
| **PWA — итого** | | **~2 рабочих дня** |
| **Expo WebView — неделя 1** | Проект, WebView экран, иконки, EAS Build preview | 3–5 дней |
| **Expo WebView — неделя 2** | Apple/Google аккаунты, скриншоты, submission | 2–3 дня |
| **Expo WebView — итого** | | **~1.5–2 недели** |
| **Expo Нативный** | JSON API, все экраны, i18n, тестирование | **4–8 недель** |

**Рекомендация**: начните с PWA (2 дня) — это даст 80% пользы для Android-пользователей немедленно. Затем Expo WebView для попадания в App Store (доп. 2 недели). Нативный клиент — если появятся требования к push-уведомлениям, камере или offline-режиму.

---

## Roadmap {#roadmap}

```
Неделя 1: PWA
├── Создать иконки (maskable.app editor)
├── Добавить app.webmanifest + FastAPI-роут /app.webmanifest
├── Добавить sw.js + роут /sw.js (scope: '/')
├── Добавить мета-теги в base.html (apple-touch-icon, theme-color, manifest)
├── Создать /offline страницу (без CDN зависимостей)
├── Добавить баннер установки (beforeinstallprompt + iOS инструкция)
└── Lighthouse audit → достичь PWA Installable ✅

Неделя 2: Тестирование PWA
├── Тест на реальном Android (Chrome) — установка A2HS
├── Тест на iOS 16.4+ (Safari) — установка + web push
├── PageSpeed Insights + Core Web Vitals
└── WCAG проверка offline-страницы (aXe)

Неделя 3–4: Expo WebView (опционально)
├── npx create-expo-app@latest --template default@sdk-57
├── Реализовать экран WebView с вашим URL
├── Настроить app.json (bundleIdentifier, permissions)
├── eas build --profile preview (тест APK на Android)
├── Apple Developer Program ($99)
├── Скриншоты, описания, Privacy Policy
└── eas submit → TestFlight → App Store

Долгосрочно: Expo Native
├── JSON API эндпоинты в FastAPI
├── Нативные экраны (login, resident dashboard, submit reading)
├── expo-notifications (push)
├── expo-camera (фото счётчика)
└── EAS Update (OTA обновления без re-submission)
```

---

## Источники {#sources}

- **web.dev/articles/add-manifest** — Web App Manifest, все поля, иконки, `id`
- **web.dev/articles/service-worker-lifecycle** — lifecycle, `skipWaiting`, `clients.claim`
- **web.dev/articles/maskable-icon** — maskable icons, safe zone 40%, инструмент maskable.app
- **web.dev/articles/offline-cookbook** — стратегии кэширования (Cache First, Network First, SWR)
- **web.dev/articles/pwa-checklist** — Core PWA Checklist, installability criteria
- **MDN: Service Worker API** — https://developer.mozilla.org/docs/Web/API/Service_Worker_API
- **MDN: beforeinstallprompt** — https://developer.mozilla.org/docs/Web/API/Window/beforeinstallprompt_event
- **Apple: Web Push for Web Apps (iOS 16.4)** — https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/
- **Apple: Supported Meta Tags** — https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariHTMLRef/Articles/MetaTags.html
- **Expo Docs: Create a project (SDK 57)** — https://docs.expo.dev/get-started/create-a-project/
- **Expo Docs: EAS Build** — https://docs.expo.dev/build/introduction/
- **W3C Web App Manifest spec** — https://w3c.github.io/manifest/
- **Chrome: PWA rich install UI (screenshots)** — https://developer.chrome.com/blog/richer-pwa-installation/