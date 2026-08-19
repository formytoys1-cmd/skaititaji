"""Мультиязычность (i18n): LV / RU / EN.

Простой словарь переводов по ключам + помощник ``t(lang, key)``. Язык хранится
в cookie ``lang`` (по умолчанию — латышский). Названия типов счётчиков берутся
из полей модели (name_lv/ru/en) через ``meter_name``.
"""
from __future__ import annotations

LANGS = ["lv", "ru", "en"]
LANG_NAMES = {"lv": "LV", "ru": "RU", "en": "EN"}
DEFAULT_LANG = "lv"


def normalize_lang(value: str | None) -> str:
    v = (value or "").lower()[:2]
    return v if v in LANGS else DEFAULT_LANG


T: dict[str, dict[str, str]] = {
    # ---- Навигация / подвал ---------------------------------------------- #
    "nav.my_flat": {"lv": "Mans dzīvoklis", "ru": "Моя квартира", "en": "My flat"},
    "nav.management": {"lv": "Pārvalde", "ru": "Управление", "en": "Management"},
    "nav.admin": {"lv": "Admin", "ru": "Админ", "en": "Admin"},
    "nav.console": {"lv": "Konsole", "ru": "Консоль", "en": "Console"},
    "nav.logout": {"lv": "Iziet", "ru": "Выйти", "en": "Log out"},
    "nav.demo": {"lv": "Demo", "ru": "Демо", "en": "Demo"},
    "nav.login": {"lv": "Ieeja", "ru": "Вход", "en": "Log in"},
    "nav.help": {"lv": "Palīdzība", "ru": "Помощь", "en": "Help"},
    "footer.copy": {
        "lv": "© Skaitītāji — demo. Integrācija: Visma Horizon REST API.",
        "ru": "© Skaitītāji — демо. Интеграция: Visma Horizon REST API.",
        "en": "© Skaitītāji — demo. Integration: Visma Horizon REST API.",
    },
    "footer.tagline": {
        "lv": "Skaitītāju rādījumu nodošanas platforma",
        "ru": "Платформа подачи показаний счётчиков",
        "en": "Meter reading submission platform",
    },
    # ---- Лендинг --------------------------------------------------------- #
    "landing.eyebrow": {
        "lv": "Ūdens · Siltums · Enerģija",
        "ru": "Вода · Тепло · Энергия",
        "en": "Water · Heat · Energy",
    },
    "landing.title": {
        "lv": "Skaitītāju rādījumu nodošana — ērti, ātri, caurspīdīgi",
        "ru": "Подача показаний счётчиков — удобно, быстро, прозрачно",
        "en": "Submit meter readings — easy, fast, transparent",
    },
    "landing.desc": {
        "lv": "Platforma dzīvokļu īpašniekiem un apsaimniekotājiem. Nododiet aukstā un "
              "karstā ūdens rādījumus dažās sekundēs. Viegli pievienojami jauni "
              "skaitītāju tipi un jebkura organizācija. Integrācija ar Visma Horizon.",
        "ru": "Платформа для жильцов и управляющих. Подавайте показания холодной и "
              "горячей воды за секунды. Легко добавляются новые типы счётчиков и любая "
              "организация. Интеграция с Visma Horizon.",
        "en": "A platform for residents and property managers. Submit cold and hot "
              "water readings in seconds. Easily add new meter types and any "
              "organization. Integration with Visma Horizon.",
    },
    "landing.enter_demo": {
        "lv": "Ienākt demo (viesis) →",
        "ru": "Войти в демо (гость) →",
        "en": "Enter demo (guest) →",
    },
    "landing.why": {"lv": "Kāpēc šī platforma", "ru": "Почему эта платформа",
                    "en": "Why this platform"},
    "landing.why_sub": {
        "lv": "Balstīta uz Latvijas tirgus un likumdošanas analīzi.",
        "ru": "Основана на анализе латвийского рынка и законодательства.",
        "en": "Based on analysis of the Latvian market and legislation.",
    },
    "landing.supported": {
        "lv": "Atbalstītie skaitītāju tipi",
        "ru": "Поддерживаемые типы счётчиков",
        "en": "Supported meter types",
    },
    "feat.types.t": {"lv": "Jebkurš skaitītāja tips", "ru": "Любой тип счётчика",
                     "en": "Any meter type"},
    "feat.types.d": {
        "lv": "Konfigurējami skaitītāju tipi — ūdens, elektrība, gāze, siltums. "
              "Jauns tips = viens ieraksts, bez koda izmaiņām.",
        "ru": "Настраиваемые типы счётчиков — вода, электричество, газ, тепло. "
              "Новый тип = одна запись, без изменений кода.",
        "en": "Configurable meter types — water, electricity, gas, heat. "
              "A new type = one record, no code changes.",
    },
    "feat.multi.t": {"lv": "Daudznomnieku (multi-tenant)", "ru": "Мультиарендность",
                     "en": "Multi-tenant"},
    "feat.multi.d": {
        "lv": "Katra organizācija (apsaimniekotājs, kooperatīvs, ūdenssaimniecība) — "
              "atsevišķa telpa ar savu zīmolu un iestatījumiem.",
        "ru": "Каждая организация (управляющий, кооператив, водовод) — отдельное "
              "пространство со своим брендом и настройками.",
        "en": "Each organization (manager, cooperative, water utility) — a separate "
              "space with its own branding and settings.",
    },
    "feat.visma.t": {"lv": "Visma Horizon integrācija", "ru": "Интеграция Visma Horizon",
                     "en": "Visma Horizon integration"},
    "feat.visma.d": {
        "lv": "Rādījumi automātiski nonāk grāmatvedības sistēmā (NĪP/KNS moduļi) bez "
              "manuālas ievades.",
        "ru": "Показания автоматически попадают в учётную систему (модули NĪP/KNS) без "
              "ручного ввода.",
        "en": "Readings automatically flow into the accounting system (NĪP/KNS "
              "modules) without manual entry.",
    },
    "feat.dash.t": {"lv": "Vadītāja panelis", "ru": "Панель управляющего",
                    "en": "Manager dashboard"},
    "feat.dash.d": {
        "lv": "Redziet, cik rādījumu nodoti, kuri vēl nav, patēriņa anomālijas un "
              "parādnieki.",
        "ru": "Видно, сколько показаний сдано, кто ещё нет, аномалии потребления и "
              "должники.",
        "en": "See how many readings are submitted, who hasn't yet, consumption "
              "anomalies and debtors.",
    },
    "feat.auth.t": {"lv": "Droša autorizācija", "ru": "Безопасный вход",
                    "en": "Secure authentication"},
    "feat.auth.d": {
        "lv": "Sagatavots Smart-ID / eParaksts / banku autentifikācijai (eIDAS).",
        "ru": "Готово к Smart-ID / eParaksts / банковскому входу (eIDAS).",
        "en": "Ready for Smart-ID / eParaksts / bank authentication (eIDAS).",
    },
    "feat.lang.t": {"lv": "LV / RU / EN", "ru": "LV / RU / EN", "en": "LV / RU / EN"},
    "feat.lang.d": {
        "lv": "Daudzvalodu saskarne, kas svarīga Latvijas kontekstā.",
        "ru": "Многоязычный интерфейс, важный в латвийском контексте.",
        "en": "A multilingual interface, important in the Latvian context.",
    },
    # ---- Вход ------------------------------------------------------------ #
    "login.title": {"lv": "Ieeja", "ru": "Вход", "en": "Log in"},
    "login.subtitle": {"lv": "Ievadiet e-pastu un paroli.",
                       "ru": "Введите e-mail и пароль.",
                       "en": "Enter your e-mail and password."},
    "login.email": {"lv": "E-pasts", "ru": "E-mail", "en": "E-mail"},
    "login.password": {"lv": "Parole", "ru": "Пароль", "en": "Password"},
    "login.enter": {"lv": "Ieiet", "ru": "Войти", "en": "Log in"},
    "login.show": {"lv": "Rādīt", "ru": "Показать", "en": "Show"},
    "login.hide": {"lv": "Slēpt", "ru": "Скрыть", "en": "Hide"},
    "login.demo_access": {"lv": "Demo piekļuve (parole visiem:",
                          "ru": "Демо-доступ (пароль у всех:",
                          "en": "Demo access (password for all:"},
    "login.quick_hint": {
        "lv": "Nospiediet pogu — lauki aizpildīsies automātiski, tad «Ieiet».",
        "ru": "Нажмите кнопку — поля заполнятся автоматически, затем «Войти».",
        "en": "Click a button — fields fill in automatically, then «Log in».",
    },
    "login.role_admin": {"lv": "Admins / moderators", "ru": "Админ / модератор",
                         "en": "Admin / moderator"},
    "login.role_manager": {"lv": "Apsaimniekotājs", "ru": "Управляющий",
                           "en": "Property manager"},
    "login.role_resident": {"lv": "Iedzīvotājs", "ru": "Житель", "en": "Resident"},
    "login.planned": {
        "lv": "Ražošanā plānots: Smart-ID · eParaksts · banku autentifikācija",
        "ru": "В продакшене планируется: Smart-ID · eParaksts · вход через банк",
        "en": "Planned for production: Smart-ID · eParaksts · bank authentication",
    },
    "login.no_account": {"lv": "Nav konta?", "ru": "Нет аккаунта?",
                         "en": "No account?"},
    "login.see_demo": {"lv": "Skatīt demo piekļuvi →", "ru": "Посмотреть демо-доступ →",
                       "en": "See demo access →"},
    "login.wake": {
        "lv": "Ja lapa neatveras uzreiz — bezmaksas serveris «pamostas» ~30 sek. "
              "Uzgaidiet un atsvaidziniet lapu.",
        "ru": "Если страница открывается не сразу — бесплатный сервер «просыпается» "
              "~30 сек. Подождите и обновите страницу.",
        "en": "If the page doesn't open immediately — the free server «wakes up» in "
              "~30 sec. Wait and refresh.",
    },
    # ---- Кабинет жителя -------------------------------------------------- #
    "res.title": {"lv": "Skaitītāju rādījumu nodošana",
                  "ru": "Подача показаний счётчиков",
                  "en": "Submit meter readings"},
    "res.period": {"lv": "Periods", "ru": "Период", "en": "Period"},
    "res.window_open": {"lv": "● Nodošana atvērta", "ru": "● Приём открыт",
                        "en": "● Submission open"},
    "res.window_closed": {
        "lv": "Ārpus nodošanas perioda (rādījumi tiks pieņemti)",
        "ru": "Вне периода подачи (показания будут приняты)",
        "en": "Outside the submission window (readings still accepted)",
    },
    "res.no_flat": {"lv": "Jūsu kontam nav piesaistīts neviens dzīvoklis.",
                    "ru": "К вашему аккаунту не привязана ни одна квартира.",
                    "en": "No apartment is linked to your account."},
    "res.flat": {"lv": "Dzīvoklis", "ru": "Квартира", "en": "Apartment"},
    "res.meters": {"lv": "skaitītāji", "ru": "счётчиков", "en": "meters"},
    "res.prev": {"lv": "Iepr.", "ru": "Пред.", "en": "Prev."},
    "res.submitted": {"lv": "Nodots", "ru": "Подано", "en": "Submitted"},
    "res.consumption": {"lv": "Patēriņš", "ru": "Расход", "en": "Consumption"},
    "res.submit": {"lv": "Nodot rādījumus", "ru": "Подать показания",
                   "en": "Submit readings"},
    "res.rule": {
        "lv": "Rādījums nevar būt mazāks par iepriekšējo. Pārāk liels patēriņš tiek "
              "atzīmēts kā anomālija.",
        "ru": "Показание не может быть меньше предыдущего. Слишком большой расход "
              "помечается как аномалия.",
        "en": "A reading can't be lower than the previous one. Excessive consumption "
              "is flagged as an anomaly.",
    },
    "res.less": {"lv": "Mazāks par iepriekšējo", "ru": "Меньше предыдущего",
                 "en": "Lower than previous"},
    "res.anomaly": {"lv": "Anomālija", "ru": "Аномалия", "en": "Anomaly"},
    # ---- Помощь / мануалы ------------------------------------------------ #
    "help.title": {"lv": "Palīdzība un pamācības", "ru": "Помощь и инструкции",
                   "en": "Help & manuals"},
    "help.subtitle": {
        "lv": "Vienkāršas soli-pa-solim pamācības ar attēliem.",
        "ru": "Простые пошаговые инструкции с картинками.",
        "en": "Simple step-by-step guides with pictures.",
    },
    "help.for_resident": {"lv": "Iedzīvotājam: kā nodot rādījumus",
                          "ru": "Жителю: как подать показания",
                          "en": "For residents: how to submit readings"},
    "help.for_manager": {"lv": "Apsaimniekotājam: panelis un sinhronizācija",
                         "ru": "Управляющему: панель и синхронизация",
                         "en": "For managers: dashboard and sync"},
    "help.for_admin": {"lv": "Administratoram: konsole un tipi",
                       "ru": "Администратору: консоль и типы",
                       "en": "For admins: console and types"},
    "help.open": {"lv": "Atvērt pamācību →", "ru": "Открыть инструкцию →",
                  "en": "Open the guide →"},
    "help.back": {"lv": "← Visas pamācības", "ru": "← Все инструкции",
                  "en": "← All guides"},
    "help.step": {"lv": "Solis", "ru": "Шаг", "en": "Step"},
    # ---- Доступность / EU / cookie --------------------------------------- #
    "a11y.skip": {"lv": "Pāriet uz saturu", "ru": "Перейти к содержимому",
                  "en": "Skip to content"},
    "nav.privacy": {"lv": "Privātums", "ru": "Приватность", "en": "Privacy"},
    "nav.accessibility": {"lv": "Pieejamība", "ru": "Доступность",
                          "en": "Accessibility"},
    "lang.aria": {"lv": "Valoda", "ru": "Язык", "en": "Language"},
    "lang.lv_full": {"lv": "Latviešu valoda", "ru": "Латышский язык",
                     "en": "Latvian"},
    "lang.ru_full": {"lv": "Krievu valoda", "ru": "Русский язык", "en": "Russian"},
    "lang.en_full": {"lv": "Angļu valoda", "ru": "Английский язык", "en": "English"},
    "cookie.text": {
        "lv": "Šī vietne izmanto tikai nepieciešamās sīkdatnes (sesija un valodas "
              "izvēle). Analītikas vai reklāmas sīkdatnes netiek izmantotas.",
        "ru": "Этот сайт использует только необходимые cookie (сессия и выбор "
              "языка). Аналитических и рекламных cookie нет.",
        "en": "This site uses only essential cookies (session and language "
              "choice). No analytics or advertising cookies.",
    },
    "cookie.ok": {"lv": "Sapratu", "ru": "Понятно", "en": "Got it"},
    "cookie.more": {"lv": "Uzzināt vairāk", "ru": "Подробнее", "en": "Learn more"},
    # ---- Приватность ----------------------------------------------------- #
    "privacy.title": {"lv": "Privātuma politika", "ru": "Политика приватности",
                      "en": "Privacy policy"},
    "privacy.intro": {
        "lv": "Mēs cienām jūsu privātumu un apstrādājam personas datus saskaņā ar "
              "ES Vispārīgo datu aizsardzības regulu (GDPR, 2016/679).",
        "ru": "Мы уважаем вашу приватность и обрабатываем персональные данные в "
              "соответствии с Общим регламентом ЕС по защите данных (GDPR, "
              "2016/679).",
        "en": "We respect your privacy and process personal data in accordance "
              "with the EU General Data Protection Regulation (GDPR, 2016/679).",
    },
    # ---- Декларация доступности ------------------------------------------ #
    "acc.title": {"lv": "Pieejamības paziņojums", "ru": "Декларация доступности",
                  "en": "Accessibility statement"},
    "acc.intro": {
        "lv": "Šī vietne cenšas nodrošināt atbilstību WCAG 2.2 AA līmenim un ES "
              "Tīmekļvietņu pieejamības direktīvai (2016/2102).",
        "ru": "Этот сайт стремится соответствовать уровню WCAG 2.2 AA и Директиве "
              "ЕС о доступности веб-сайтов (2016/2102).",
        "en": "This website strives to conform to WCAG 2.2 level AA and the EU Web "
              "Accessibility Directive (2016/2102).",
    },
}


def t(lang: str, key: str) -> str:
    lang = normalize_lang(lang)
    entry = T.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key


def meter_name(meter_type, lang: str) -> str:
    """Название типа счётчика на нужном языке (из модели)."""
    lang = normalize_lang(lang)
    if meter_type is None:
        return ""
    return {
        "lv": meter_type.name_lv,
        "ru": meter_type.name_ru,
        "en": meter_type.name_en,
    }.get(lang, meter_type.name_lv)
