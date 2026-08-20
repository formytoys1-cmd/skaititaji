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
    # ---- PWA / офлайн / установка ----------------------------------------- #
    "offline.title": {"lv": "Nav savienojuma", "ru": "Нет соединения",
                      "en": "You're offline"},
    "offline.body": {
        "lv": "Šķiet, ka interneta savienojums ir zudis. Pārbaudiet tīklu un mēģiniet vēlreiz.",
        "ru": "Похоже, пропало интернет-соединение. Проверьте сеть и попробуйте снова.",
        "en": "It looks like your internet connection is gone. Check your network and try again.",
    },
    "offline.retry": {"lv": "Mēģināt vēlreiz", "ru": "Повторить", "en": "Retry"},
    "offline.home": {"lv": "Uz sākumu", "ru": "На главную", "en": "Go home"},
    "pwa.install": {"lv": "Instalēt lietotni", "ru": "Установить приложение",
                    "en": "Install app"},
    "pwa.install_ios": {
        "lv": "Lai instalētu: nospiediet «Kopīgot» un «Pievienot sākuma ekrānam».",
        "ru": "Чтобы установить: нажмите «Поделиться», затем «На экран Домой».",
        "en": "To install: tap Share, then “Add to Home Screen”.",
    },
    "pwa.dismiss": {"lv": "Aizvērt", "ru": "Закрыть", "en": "Dismiss"},
    # ---- Страница «Поделиться» / QR -------------------------------------- #
    "share.nav": {"lv": "Kopīgot", "ru": "Поделиться", "en": "Share"},
    "share.title": {"lv": "Kopīgot piekļuvi", "ru": "Поделиться доступом",
                    "en": "Share access"},
    "share.subtitle": {
        "lv": "Noskenējiet QR ar telefonu, lai atvērtu vietni vai instalētu lietotni.",
        "ru": "Отсканируйте QR телефоном, чтобы открыть сайт или установить приложение.",
        "en": "Scan the QR with your phone to open the site or install the app.",
    },
    "share.qr_site": {"lv": "Vietne", "ru": "Сайт", "en": "Website"},
    "share.qr_site_hint": {
        "lv": "Atveriet skaitītāju nodošanas vietni.",
        "ru": "Открыть сайт подачи показаний счётчиков.",
        "en": "Open the meter-reading website.",
    },
    "share.qr_app": {"lv": "Lietotne telefonā", "ru": "Приложение на телефон",
                     "en": "Phone app"},
    "share.qr_app_hint": {
        "lv": "Instalējiet kā lietotni sākuma ekrānā (iOS/Android).",
        "ru": "Установите как приложение на домашний экран (iOS/Android).",
        "en": "Install as an app on your home screen (iOS/Android).",
    },
    "share.install_title": {"lv": "Kā instalēt lietotni",
                            "ru": "Как установить приложение",
                            "en": "How to install the app"},
    "share.install_ios": {
        "lv": "iPhone (Safari): pieskarieties «Kopīgot» → «Pievienot sākuma ekrānam».",
        "ru": "iPhone (Safari): нажмите «Поделиться» → «На экран Домой».",
        "en": "iPhone (Safari): tap Share → “Add to Home Screen”.",
    },
    "share.install_android": {
        "lv": "Android (Chrome): izvēlne → «Instalēt lietotni» (vai poga lapā).",
        "ru": "Android (Chrome): меню → «Установить приложение» (или кнопка на странице).",
        "en": "Android (Chrome): menu → “Install app” (or the button on the page).",
    },
    "share.copy": {"lv": "Kopēt saiti", "ru": "Копировать ссылку", "en": "Copy link"},
    "share.copied": {"lv": "Nokopēts!", "ru": "Скопировано!", "en": "Copied!"},
    "share.print": {"lv": "Drukāt", "ru": "Печать", "en": "Print"},
    "share.download_qr": {"lv": "Lejupielādēt QR", "ru": "Скачать QR",
                          "en": "Download QR"},
    "share.stores_soon": {
        "lv": "App Store un Google Play versijas top — pagaidām instalējiet kā PWA.",
        "ru": "Версии для App Store и Google Play готовятся — пока установите как PWA.",
        "en": "App Store and Google Play versions are coming — install as a PWA for now.",
    },
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
    "res.verified_until": {"lv": "Verificēts līdz", "ru": "Поверка до",
                           "en": "Verified until"},
    "res.verify_soon": {"lv": "drīz jāverificē", "ru": "скоро поверка",
                        "en": "verification due soon"},
    "res.verify_expired": {"lv": "verifikācija beigusies",
                           "ru": "поверка истекла", "en": "verification expired"},
    # ---- Консоль модератора: файловое поле -------------------------------- #
    "inbox.choose_files": {"lv": "Izvēlēties failus", "ru": "Выбрать файлы",
                           "en": "Choose files"},
    "inbox.no_file": {"lv": "Fails nav izvēlēts", "ru": "Файл не выбран",
                      "en": "No file chosen"},
    "inbox.files_n": {"lv": "faili izvēlēti", "ru": "файлов выбрано",
                      "en": "files selected"},
    "inbox.attach_hint": {
        "lv": "Pievienot failus (formas, ekrānšāviņi) — nav obligāti",
        "ru": "Прикрепить файлы (формы, скриншоты) — необязательно",
        "en": "Attach files (forms, screenshots) — optional",
    },
    "inbox.reply_title": {"lv": "Atbilde aģentam", "ru": "Ответ агенту",
                          "en": "Reply to agent"},
    "inbox.newest_top": {"lv": "Jaunākie ziņojumi augšā",
                         "ru": "Новые сообщения сверху",
                         "en": "Newest messages on top"},
    "inbox.send": {"lv": "Sūtīt aģentam", "ru": "Отправить агенту",
                   "en": "Send to agent"},
    "inbox.change_status": {"lv": "Mainīt statusu", "ru": "Изменить статус",
                            "en": "Change status"},
    "inbox.apply": {"lv": "Piemērot", "ru": "Применить", "en": "Apply"},
    "inbox.attachments": {"lv": "Pievienotie faili", "ru": "Прикреплённые файлы",
                          "en": "Attached files"},
    "inbox.all_threads": {"lv": "Visi norādījumi", "ru": "Все обращения",
                          "en": "All threads"},
    "inbox.author_agent": {"lv": "Aģents", "ru": "Агент", "en": "Agent"},
    "inbox.author_moderator": {"lv": "Moderators", "ru": "Модератор",
                               "en": "Moderator"},
    "inbox.new_reply": {"lv": "Jauna aģenta atbilde!", "ru": "Новый ответ агента!",
                        "en": "New agent reply!"},
    # ---- Консоль: заголовки, форма, список -------------------------------- #
    "inbox.console_title": {"lv": "Moderatora konsole", "ru": "Консоль модератора",
                            "en": "Moderator console"},
    "inbox.console_sub": {
        "lv": "Nosūtiet norādījumus aģentam pilnai vai daļējai vietnes pārstrādei. Aģents atbild šeit.",
        "ru": "Отправляйте агенту указания на полную или частичную переработку сайта. Агент отвечает здесь.",
        "en": "Send the agent instructions for full or partial site rework. The agent replies here.",
    },
    "inbox.new_instruction": {"lv": "Jauns norādījums", "ru": "Новое указание",
                              "en": "New instruction"},
    "inbox.form_hint": {
        "lv": "Aizpildiet un nosūtiet — aģents saņems paziņojumu.",
        "ru": "Заполните и отправьте — агент получит уведомление.",
        "en": "Fill in and send — the agent will be notified.",
    },
    "inbox.title_ph": {"lv": "Virsraksts (īss)", "ru": "Заголовок (кратко)",
                       "en": "Title (short)"},
    "inbox.kind": {"lv": "Veids", "ru": "Тип", "en": "Type"},
    "inbox.scope_partial": {"lv": "Daļēja pārstrāde", "ru": "Частичная переработка",
                            "en": "Partial rework"},
    "inbox.scope_full": {"lv": "Pilna pārstrāde", "ru": "Полная переработка",
                         "en": "Full rework"},
    "inbox.scope_bug": {"lv": "Kļūdas labojums", "ru": "Исправление ошибки",
                        "en": "Bug fix"},
    "inbox.scope_idea": {"lv": "Ideja / priekšlikums", "ru": "Идея / предложение",
                         "en": "Idea / suggestion"},
    "inbox.priority": {"lv": "Prioritāte", "ru": "Приоритет", "en": "Priority"},
    "inbox.prio_normal": {"lv": "Prioritāte: parasta", "ru": "Приоритет: обычный",
                          "en": "Priority: normal"},
    "inbox.prio_high": {"lv": "Prioritāte: augsta", "ru": "Приоритет: высокий",
                        "en": "Priority: high"},
    "inbox.prio_low": {"lv": "Prioritāte: zema", "ru": "Приоритет: низкий",
                       "en": "Priority: low"},
    "inbox.high_priority": {"lv": "augsta prioritāte", "ru": "высокий приоритет",
                            "en": "high priority"},
    "inbox.area_ph": {
        "lv": "Zona / lapa (piem. iedzīvotāja panelis)",
        "ru": "Зона / страница (напр. кабинет жителя)",
        "en": "Area / page (e.g. resident dashboard)",
    },
    "inbox.body_ph": {"lv": "Detalizēti aprakstiet, ko izmainīt...",
                      "ru": "Подробно опишите, что изменить...",
                      "en": "Describe in detail what to change..."},
    "inbox.threads": {"lv": "Norādījumi", "ru": "Обращения", "en": "Threads"},
    "inbox.no_threads": {
        "lv": "Vēl nav norādījumu. Izveidojiet pirmo pa kreisi.",
        "ru": "Обращений пока нет. Создайте первое слева.",
        "en": "No threads yet. Create the first one on the left.",
    },
    "inbox.msg_count": {"lv": "ziņas", "ru": "сообщ.", "en": "msgs"},
    "inbox.last": {"lv": "pēdējais", "ru": "последний", "en": "last"},
    "inbox.created": {"lv": "izveidots", "ru": "создано", "en": "created"},
    "inbox.zone": {"lv": "zona", "ru": "зона", "en": "area"},
    "inbox.reply_ph": {"lv": "Atbilde vai precizējums aģentam...",
                       "ru": "Ответ или уточнение агенту...",
                       "en": "Reply or clarification to the agent..."},
    "inbox.status_done": {"lv": "Pieņemts (done)", "ru": "Принято (done)",
                          "en": "Accepted (done)"},
    "inbox.status_reject": {"lv": "Atcelt (rejected)", "ru": "Отклонить (rejected)",
                            "en": "Reject (rejected)"},
    "inbox.status_reopen": {"lv": "Atkārtoti aģentam (new)",
                            "ru": "Снова агенту (new)", "en": "Back to agent (new)"},
    # Ярлыки статусов треда (бейджи)
    "inbox.st_new": {"lv": "Jauns", "ru": "Новое", "en": "New"},
    "inbox.st_in_progress": {"lv": "Darbā", "ru": "В работе", "en": "In progress"},
    "inbox.st_needs_clarification": {"lv": "Gaida precizējumu",
                                     "ru": "Ждёт уточнения", "en": "Needs clarification"},
    "inbox.st_ready": {"lv": "Pārbaudei", "ru": "На проверку", "en": "For review"},
    "inbox.st_done": {"lv": "Pabeigts", "ru": "Завершено", "en": "Done"},
    "inbox.st_rejected": {"lv": "Atcelts", "ru": "Отменено", "en": "Cancelled"},
    # Flash-уведомления консоли
    "inbox.flash_created": {"lv": "Norādījums nosūtīts aģentam",
                            "ru": "Указание отправлено агенту",
                            "en": "Instruction sent to the agent"},
    "inbox.flash_msg_sent": {"lv": "Ziņa nosūtīta aģentam",
                             "ru": "Сообщение отправлено агенту",
                             "en": "Message sent to the agent"},
    "inbox.flash_not_found": {"lv": "Norādījums nav atrasts.",
                              "ru": "Обращение не найдено.",
                              "en": "Thread not found."},
    "inbox.flash_status_changed": {"lv": "Statuss mainīts",
                                   "ru": "Статус изменён", "en": "Status changed"},
    "inbox.flash_bad_status": {"lv": "Nederīgs statuss.",
                               "ru": "Недопустимый статус.", "en": "Invalid status."},
    "inbox.flash_files": {"lv": "fails(-i)", "ru": "файл(ов)", "en": "file(s)"},
    # ---- История и график (B) -------------------------------------------- #
    "res.history": {"lv": "Rādījumu vēsture", "ru": "История показаний",
                    "en": "Reading history"},
    "res.history_link": {"lv": "Vēsture un grafiks", "ru": "История и график",
                         "en": "History & chart"},
    "res.no_history": {"lv": "Vēl nav rādījumu vēstures.",
                       "ru": "Истории показаний пока нет.",
                       "en": "No reading history yet."},
    "res.period_col": {"lv": "Periods", "ru": "Период", "en": "Period"},
    "res.reading_col": {"lv": "Rādījums", "ru": "Показание", "en": "Reading"},
    "res.chart_title": {"lv": "Patēriņa grafiks", "ru": "График расхода",
                        "en": "Consumption chart"},
    "res.estimated": {"lv": "aprēķināts (§41)", "ru": "расчётное (§41)",
                      "en": "estimated (§41)"},
    "res.avg_12m": {"lv": "Vidēji (12 mēn.)", "ru": "Средн. (12 мес.)",
                    "en": "Avg (12 mo.)"},
    "res.export_csv": {"lv": "Eksportēt CSV", "ru": "Экспорт в CSV",
                       "en": "Export CSV"},
    # ---- §41 прогноз (C) -------------------------------------------------- #
    "res.forecast": {
        "lv": "Ja nenodosiet, tiks aprēķināts vidējais",
        "ru": "Если не подадите — начислим среднее",
        "en": "If not submitted, average will be estimated",
    },
    "res.forecast_note": {
        "lv": "Saskaņā ar MK noteikumiem (§41), ja rādījums nav nodots, patēriņu "
              "aprēķina pēc vidējā par pēdējiem 12 mēnešiem.",
        "ru": "Согласно правилам КМ (§41), если показание не подано, расход "
              "рассчитывают по среднему за последние 12 месяцев.",
        "en": "Per Cabinet rules (§41), if no reading is submitted, consumption is "
              "estimated from the last 12-month average.",
    },
    # ---- Печатная форма (D) ---------------------------------------------- #
    "res.print": {"lv": "Drukāt veidlapu", "ru": "Печать формы",
                  "en": "Print form"},
    "res.print_link": {"lv": "Druka", "ru": "Печать", "en": "Print"},
    "res.print_title": {"lv": "Skaitītāju rādījumu nodošanas veidlapa",
                        "ru": "Форма подачи показаний счётчиков",
                        "en": "Meter reading submission form"},
    "res.col_serial": {"lv": "Skait. Nr.", "ru": "№ счёт.", "en": "Meter No."},
    "res.col_verified": {"lv": "Der. līdz", "ru": "Поверка до", "en": "Valid until"},
    "res.col_start": {"lv": "Sākumā", "ru": "Начало", "en": "Start"},
    "res.col_end": {"lv": "Beigas", "ru": "Конец", "en": "End"},
    "res.col_type": {"lv": "Pakalpojums", "ru": "Услуга", "en": "Service"},
    "res.print_hint": {
        "lv": "Aizpildiet aili «Beigas» un iesniedziet apsaimniekotājam.",
        "ru": "Заполните столбец «Конец» и передайте управляющему.",
        "en": "Fill in the «End» column and hand it to the manager.",
    },
    "res.do_print": {"lv": "Drukāt", "ru": "Печать", "en": "Print"},
    "res.signature": {"lv": "Paraksts", "ru": "Подпись", "en": "Signature"},
    "res.date": {"lv": "Datums", "ru": "Дата", "en": "Date"},
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
    # ---- Announcement bar / 404 / trust --------------------------------- #
    "announce.label": {"lv": "Paziņojums", "ru": "Объявление", "en": "Announcement"},
    "announce.dismiss": {"lv": "Aizvērt paziņojumu", "ru": "Закрыть объявление",
                         "en": "Dismiss announcement"},
    "announce.window_open": {
        "lv": "Rādījumu nodošana ir atvērta līdz mēneša {day}. datumam.",
        "ru": "Приём показаний открыт до {day} числа месяца.",
        "en": "Reading submission is open until day {day} of the month.",
    },
    "trust.title": {"lv": "Uzticama un atbilstoša", "ru": "Надёжно и соответствует",
                    "en": "Trusted & compliant"},
    "trust.wcag": {"lv": "Pieejamība WCAG 2.2 AA", "ru": "Доступность WCAG 2.2 AA",
                   "en": "WCAG 2.2 AA accessible"},
    "trust.gdpr": {"lv": "GDPR atbilstība", "ru": "Соответствие GDPR",
                   "en": "GDPR compliant"},
    "trust.visma": {"lv": "Visma Horizon integrācija", "ru": "Интеграция Visma Horizon",
                    "en": "Visma Horizon integration"},
    "trust.langs": {"lv": "3 valodas: LV / RU / EN", "ru": "3 языка: LV / RU / EN",
                    "en": "3 languages: LV / RU / EN"},
    "err404.title": {"lv": "Lapa nav atrasta", "ru": "Страница не найдена",
                     "en": "Page not found"},
    "err404.text": {
        "lv": "Diemžēl šāda lapa neeksistē vai ir pārvietota.",
        "ru": "К сожалению, такой страницы нет или она перемещена.",
        "en": "Sorry, this page doesn't exist or has moved.",
    },
    "err404.home": {"lv": "Uz sākumu", "ru": "На главную", "en": "Go home"},
    "landing.trust_intro": {
        "lv": "Veidots pēc augstākajiem standartiem:",
        "ru": "Построено по высоким стандартам:",
        "en": "Built to high standards:",
    },
    # ---- Регистрация жителя / управление -------------------------------- #
    "nav.register": {"lv": "Reģistrēties", "ru": "Регистрация", "en": "Sign up"},
    "nav.objects": {"lv": "Objekti", "ru": "Объекты", "en": "Properties"},
    "reg.title": {"lv": "Reģistrācija", "ru": "Регистрация", "en": "Sign up"},
    "reg.subtitle": {
        "lv": "Izveidojiet kontu, lai nodotu sava dzīvokļa rādījumus.",
        "ru": "Создайте аккаунт, чтобы подавать показания вашей квартиры.",
        "en": "Create an account to submit your apartment's readings.",
    },
    "reg.name": {"lv": "Vārds, uzvārds", "ru": "Имя и фамилия", "en": "Full name"},
    "reg.email": {"lv": "E-pasts", "ru": "E-mail", "en": "E-mail"},
    "reg.password": {"lv": "Parole", "ru": "Пароль", "en": "Password"},
    "reg.pw_len": {"lv": "Vismaz 8 rakstzīmes", "ru": "Минимум 8 символов",
                   "en": "At least 8 characters"},
    "reg.pw_letter": {"lv": "Satur burtu", "ru": "Содержит букву",
                      "en": "Contains a letter"},
    "reg.pw_digit": {"lv": "Satur ciparu", "ru": "Содержит цифру",
                     "en": "Contains a digit"},
    "reg.pw_show": {"lv": "Rādīt paroli", "ru": "Показать пароль",
                    "en": "Show password"},
    "reg.account": {"lv": "Konta numurs", "ru": "Номер лицевого счёта",
                    "en": "Account number"},
    "reg.account_hint": {
        "lv": "Konta numuru izsniedz jūsu apsaimniekotājs (norādīts rēķinā).",
        "ru": "Номер счёта выдаёт ваш управляющий (указан в квитанции).",
        "en": "Your property manager provides the account number (on your invoice).",
    },
    "reg.submit": {"lv": "Reģistrēties", "ru": "Зарегистрироваться", "en": "Sign up"},
    "reg.have_account": {"lv": "Jau ir konts?", "ru": "Уже есть аккаунт?",
                         "en": "Already have an account?"},
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
