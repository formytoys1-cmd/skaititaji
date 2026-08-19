"""Контент мануалов (помощь) на 3 языках.

Каждый гайд — список шагов. Шаг: (image_basename, {lang: title}, {lang: body}).
Картинки берутся из /static/img/help/{image}_{lang}.png (с фолбэком на _lv).
"""
from __future__ import annotations

GUIDES = {
    "resident": {
        "icon": "🏠",
        "title": {"lv": "Iedzīvotājam: kā nodot rādījumus",
                  "ru": "Жителю: как подать показания",
                  "en": "For residents: how to submit readings"},
        "steps": [
            (
                "resident_login",
                {"lv": "1. Ieejiet sistēmā",
                 "ru": "1. Войдите в систему",
                 "en": "1. Log in"},
                {"lv": "Atveriet lapu un nospiediet «Ieeja». Demo režīmā nospiediet "
                       "pogu «Iedzīvotājs» — lauki aizpildīsies paši, tad «Ieiet». "
                       "Parole: demo1234.",
                 "ru": "Откройте сайт и нажмите «Вход». В демо нажмите кнопку "
                       "«Житель» — поля заполнятся сами, затем «Войти». Пароль: "
                       "demo1234.",
                 "en": "Open the site and click «Log in». In demo, click the "
                       "«Resident» button — fields fill in automatically, then "
                       "«Log in». Password: demo1234."},
            ),
            (
                "resident_dashboard",
                {"lv": "2. Atrodiet savus skaitītājus",
                 "ru": "2. Найдите свои счётчики",
                 "en": "2. Find your meters"},
                {"lv": "Redzēsiet sava dzīvokļa skaitītājus: aukstais un karstais "
                       "ūdens. Pie katra ir iepriekšējais rādījums un datums.",
                 "ru": "Вы увидите счётчики вашей квартиры: холодная и горячая "
                       "вода. У каждого показано предыдущее показание и дата.",
                 "en": "You'll see your apartment meters: cold and hot water. Each "
                       "shows the previous reading and date."},
            ),
            (
                "resident_enter",
                {"lv": "3. Ievadiet rādījumu",
                 "ru": "3. Введите показание",
                 "en": "3. Enter the reading"},
                {"lv": "Ievadiet skaitītāja pašreizējo rādījumu laukā pa labi. "
                       "Sistēma uzreiz parāda patēriņu. Ja skaitlis mazāks par "
                       "iepriekšējo vai pārāk liels — parādās brīdinājums.",
                 "ru": "Введите текущее показание счётчика в поле справа. Система "
                       "сразу покажет расход. Если число меньше предыдущего или "
                       "слишком большое — появится предупреждение.",
                 "en": "Enter the meter's current reading in the field on the "
                       "right. The system instantly shows consumption. If the "
                       "number is lower than before or too high — a warning "
                       "appears."},
            ),
            (
                "resident_submit",
                {"lv": "4. Nosūtiet",
                 "ru": "4. Отправьте",
                 "en": "4. Submit"},
                {"lv": "Nospiediet «Nodot rādījumus». Parādīsies apstiprinājums. "
                       "Rādījumus var pārsūtīt atkārtoti — jaunais aizstās veco.",
                 "ru": "Нажмите «Подать показания». Появится подтверждение. Можно "
                       "подать повторно — новое заменит старое.",
                 "en": "Click «Submit readings». A confirmation appears. You can "
                       "resubmit — the new value replaces the old one."},
            ),
        ],
    },
    "manager": {
        "icon": "🧑‍💼",
        "title": {"lv": "Apsaimniekotājam: panelis un sinhronizācija",
                  "ru": "Управляющему: панель и синхронизация",
                  "en": "For managers: dashboard and sync"},
        "steps": [
            (
                "manager_dashboard",
                {"lv": "1. Pārvaldes panelis",
                 "ru": "1. Панель управления",
                 "en": "1. Management dashboard"},
                {"lv": "Ieejiet kā «Apsaimniekotājs». Redzēsiet nodošanas gaitu "
                       "(%), cik skaitītāju nodoti, kuri vēl nav, un anomālijas.",
                 "ru": "Войдите как «Управляющий». Видно прогресс подачи (%), "
                       "сколько счётчиков сдано, кто ещё нет, и аномалии.",
                 "en": "Log in as «Manager». You see submission progress (%), how "
                       "many meters are submitted, who hasn't yet, and anomalies."},
            ),
            (
                "manager_table",
                {"lv": "2. Skaitītāju statuss",
                 "ru": "2. Статус счётчиков",
                 "en": "2. Meter status"},
                {"lv": "Tabulā redzams katrs skaitītājs: rādījums, patēriņš un "
                       "statuss. Anomālijas izceltas ar dzeltenu krāsu.",
                 "ru": "В таблице виден каждый счётчик: показание, расход и "
                       "статус. Аномалии подсвечены жёлтым.",
                 "en": "The table shows each meter: reading, consumption and "
                       "status. Anomalies are highlighted in yellow."},
            ),
            (
                "manager_sync",
                {"lv": "3. Sinhronizācija ar Visma Horizon",
                 "ru": "3. Синхронизация с Visma Horizon",
                 "en": "3. Sync with Visma Horizon"},
                {"lv": "Nospiediet «Sinhronizēt ar Visma Horizon». Rādījumi tiek "
                       "nosūtīti uz grāmatvedības sistēmu, un ieraksts parādās "
                       "integrācijas žurnālā.",
                 "ru": "Нажмите «Синхронизировать с Visma Horizon». Показания "
                       "отправляются в учётную систему, а запись появляется в "
                       "журнале интеграции.",
                 "en": "Click «Sync with Visma Horizon». Readings are sent to the "
                       "accounting system, and an entry appears in the integration "
                       "log."},
            ),
        ],
    },
    "admin": {
        "icon": "⚙️",
        "title": {"lv": "Administratoram: konsole un tipi",
                  "ru": "Администратору: консоль и типы",
                  "en": "For admins: console and types"},
        "steps": [
            (
                "admin_dashboard",
                {"lv": "1. Administrācija",
                 "ru": "1. Администрирование",
                 "en": "1. Administration"},
                {"lv": "Ieejiet kā «Admins». Redzēsiet organizācijas, skaitītāju "
                       "tipu katalogu un varat pievienot jaunu tipu bez koda.",
                 "ru": "Войдите как «Админ». Видны организации, каталог типов "
                       "счётчиков; можно добавить новый тип без кода.",
                 "en": "Log in as «Admin». You see organizations, the meter type "
                       "catalog, and can add a new type without code."},
            ),
            (
                "admin_console",
                {"lv": "2. Moderatora konsole (atsauksmes)",
                 "ru": "2. Консоль модератора (обратная связь)",
                 "en": "2. Moderator console (feedback)"},
                {"lv": "Sadaļā «Konsole» varat nosūtīt norādījumus aģentam par "
                       "izmaiņām vietnē un pievienot failus (piem., papīra formas). "
                       "Aģents atbild tajā pašā sarakstē.",
                 "ru": "В разделе «Консоль» можно отправить указания агенту по "
                       "изменениям сайта и приложить файлы (напр., бумажные формы). "
                       "Агент отвечает в той же переписке.",
                 "en": "In «Console» you can send instructions to the agent about "
                       "site changes and attach files (e.g., paper forms). The "
                       "agent replies in the same thread."},
            ),
        ],
    },
}


def guide_localized(guide_key: str, lang: str) -> dict | None:
    g = GUIDES.get(guide_key)
    if not g:
        return None
    lang = lang if lang in ("lv", "ru", "en") else "lv"
    return {
        "key": guide_key,
        "icon": g["icon"],
        "title": g["title"].get(lang, g["title"]["lv"]),
        "steps": [
            {
                "image": img,
                "title": tt.get(lang, tt["lv"]),
                "body": bb.get(lang, bb["lv"]),
            }
            for (img, tt, bb) in g["steps"]
        ],
    }
