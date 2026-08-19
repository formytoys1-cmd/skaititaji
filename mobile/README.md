# Skaitītāji — мобильное приложение (Expo / React Native)

Нативная оболочка для iOS и Android, которая публикуется в **App Store** и
**Google Play**. Сейчас это **WebView-обёртка** вокруг уже готового адаптивного
сайта/PWA `https://skaititaji.onrender.com` — самый быстрый путь получить
приложение в сторах без переписывания UI. Дальше отдельные экраны можно
переносить на нативный интерфейс, дергая тот же backend.

> ⚠️ Это стартовый каркас. Сборку/публикацию нужно запускать на машине с
> установленным Node 18+, Expo CLI и (для сборки) аккаунтом Expo EAS. Здесь код
> подготовлен и провалидирован по синтаксису, но не собирался в бинарь.

## Что уже есть

- `App.js` — экран с `WebView`, который грузит сайт, показывает лоадер,
  обрабатывает офлайн (экран «Nav savienojuma» + «Повторить»), аппаратную
  кнопку «назад» на Android и pull-to-refresh.
- `app.json` — конфигурация Expo: имя, иконки, splash (капля на фирменном
  синем `#0369a1`), bundle id `lv.skaititaji.app`, `extra.siteUrl`.
- `assets/` — `icon.png` (1024), `adaptive-icon.png` (Android), `splash.png`.
- `package.json`, `babel.config.js`, `index.js` — стандартный Expo-бутстрап.

## Быстрый старт (локально)

```bash
cd mobile
npm install
npx expo start           # откроется Expo Dev Tools; QR — для Expo Go на телефоне
# или:
npx expo start --ios     # запуск в iOS-симуляторе (нужен Xcode, macOS)
npx expo start --android # запуск в Android-эмуляторе (нужен Android Studio)
```

Сменить целевой сайт — в `app.json` → `expo.extra.siteUrl`.

## Два пути развития

| Путь | Скорость | Плюсы | Когда |
|------|----------|-------|-------|
| **A. WebView-обёртка (сейчас)** | 1–2 дня до сборки | Один UI/логика, мгновенные обновления через деплой сайта | Старт, MVP в сторах |
| **B. Нативные экраны + JSON API** | недели | Нативный UX, офлайн, пуши, камера для фото счётчика | Когда нужен полноценный native |

Для пути B бэкенд уже частично готов отдавать JSON (`/agent/api/*`, `/api/*`);
нужно добавить публичные REST-эндпоинты авторизации и подачи показаний.

## Дорожная карта публикации

### 1. Подготовка аккаунтов
- **Apple Developer Program** — $99/год (обязательно для App Store).
- **Google Play Console** — $25 разово.
- Аккаунт **Expo** (бесплатно) для EAS Build.

### 2. Сборка через EAS
```bash
npm install -g eas-cli
eas login
eas build:configure
eas build -p android --profile production   # .aab для Google Play
eas build -p ios --profile production        # .ipa для App Store (нужен Apple акк.)
```

### 3. Ассеты для сторов (подготовить заранее)
- Иконка 1024×1024 (есть: `assets/icon.png`).
- Скриншоты: iPhone 6.7"/6.5"/5.5", iPad, Android phone/tablet.
- Описание на LV/RU/EN, ключевые слова, категория «Utilities».
- Политика конфиденциальности (у нас есть страница `/privatums`).
- Возрастной рейтинг, контактные данные.

### 4. Отправка на ревью
- iOS: через App Store Connect (Transporter/EAS Submit).
- Android: через Play Console (`eas submit -p android`).

### 5. После релиза
- OTA-обновления JS через `eas update` (без повторного ревью для JS-изменений).
- Пуш-уведомления: `expo-notifications` (напоминания о подаче показаний —
  из ресёрча конкурентов это высокоценная фича).

## Замечания по соответствию сторам

- **Apple** может отклонить «просто сайт в WebView», если приложение не даёт
  достаточной нативной ценности. Поэтому для App Store желательно добавить хотя
  бы: нативные пуш-напоминания, офлайн-экран (есть), нативную навигацию/таб-бар,
  либо часть экранов на native (путь B).
- **Google Play** к WebView лояльнее; альтернатива — **TWA (Trusted Web
  Activity)** прямо из PWA через Bubblewrap.

## Связанные материалы
- Отчёт по мобилизации: [`docs/night/research_mobile_pwa_native.md`](../docs/night/research_mobile_pwa_native.md)
- PWA (веб-версия «приложения») уже работает: манифест `/manifest.webmanifest`,
  service worker `/sw.js` — сайт ставится на домашний экран без сторов.
