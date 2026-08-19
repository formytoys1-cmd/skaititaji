[Turn 0]
У меня теперь достаточно данных для исчерпывающего отчёта. Составляю его.

---

# Детальный отчёт: Visma Horizon REST API

## Итоговое резюме

Visma Horizon REST API — это полноценный REST API стандарта OpenAPI 3.0.1, встроенный в ERP-систему Horizon (версия 620.4). Сайт документации `https://horizon-rest-doc.visma.lv/lv` — это Single Page Application (Vue.js), которое обращается к бэкенду через URL-пространство `/_/API/`. Весь API задокументирован в виде отдельных сервисов. Для задачи учёта показаний счётчиков и ЖКХ-биллинга в системе есть обширный модуль **NĪP** (Nekustamo Īpašumu Pārvaldība — управление недвижимостью) и модуль **KNS** (Komunālo Norēķinu Sistēma — система коммунальных расчётов).

---

## 1. Базовый URL, версионирование, хостинг

### Архитектура хостинга

**On-premise**: Visma Horizon — это устанавливаемая на сервер ERP-система. Каждый клиент (управляющая компания) имеет **свой собственный сервер** с Horizon. Документационный сайт `horizon-rest-doc.visma.lv` — это **демо-стенд/документация** одного конкретного экземпляра Horizon, принадлежащего Visma Latvia.

При реальной интеграции базовый URL будет выглядеть так:
```
https://<customer-server>/API/rest/
```
Например, на демо-стенде это:
```
/_/API/rest/{ServiceCode}
```
(через проксирующий слой документационного сайта).

### API версионирование

Версия API **не встроена в URL**. Текущая версия системы — **620.4** (указана в `info.version` каждой OpenAPI спецификации). Версия отображается в заголовке `info.version`, но в пути эндпоинтов не фигурирует. URL имеют вид:

```
/API/rest/TdmKNSkaBL
/API/rest/TdmPNSRekBL
/API/rest/TdmPNSSkaLigRadSL
```

### Структура URL

- **Документация сервисов**: `https://horizon-rest-doc.visma.lv/_/API/ServiceTree` → список всех сервисов (JSON)
- **OpenAPI спецификация сервиса**: `/_/API/HorRest/Services/{ServiceCode}/Json`
- **OpenAPI UI модель**: `/_/API/OpenApi/OpenApiUIModel/{ServiceCode}`
- **Реальный API (через прокси доки)**: `/_/API/rest/{ServiceCode}/{path}`
- **На реальном сервере клиента**: `https://server/API/rest/{ServiceCode}/{path}`

### Ключевые системные эндпоинты (без аутентификации)

```
GET /API/rest/global                     → системная информация
GET /API/rest/global/agentVersion        → текущая версия Horizon
GET /API/rest/global/healthCheck         → проверка доступности
```

Источники: `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/global`

---

## 2. Аутентификация

### Механизм: HTTP Basic Authentication

API использует **HTTP Basic Auth** (логин + пароль). Это стандартная аутентификация через заголовок:

```http
Authorization: Basic <base64(login:password)>
```

Аутентификация — сессионная с кэшированием в `localStorage` на стороне клиента документации.

### Эндпоинты аутентификации (выявлены из JS-кода `app.3f38456b.js`)

**1. Проверка/логин с логином/паролем:**
```http
POST /_/API/restAuth
Content-Type: application/json

{
  "Login": "имя_пользователя",
  "Password": "пароль"
}
```
Ответ: `200 OK` при успехе. Учётные данные затем используются для формирования `Basic` заголовка.

**2. Проверка аутентификации через приложение (AppAuth):**
```http
POST /_/API/restAuth/UsingAppAuth
Content-Type: application/json
```
Возвращает `{login, password}` если система поддерживает SSO/AppAuth.

**3. Логаут:**
```http
GET /_/Account/Logout?ReturnUrl=...
```

**4. Логин через UI:**
```http
GET /_/Account/Login?ReturnUrl=...
```

### Практический пример запроса с аутентификацией:

```http
GET /API/rest/TdmKNSkaBL HTTP/1.1
Host: <horizon-server>
Authorization: Basic dXNlcjpwYXNz
Accept: application/json
```

### Необходимые учётные данные

Это **логин и пароль пользователя Horizon**. Нужен пользователь с правами на соответствующие модули (NĪP, KNS). Отдельного API-ключа или OAuth нет — только Basic Auth.

---

## 3. Форматы данных, соглашения, параметры запросов

### Форматы

API поддерживает **оба формата** — JSON и XML:
- `Content-Type: application/json` / `Accept: application/json`
- `Content-Type: application/xml` / `Accept: application/xml`
- `Content-Type: text/xml`
- `Content-Type: multipart/form-data` (для создания записей с файлами)
- `Content-Type: application/x-www-form-urlencoded` (для вспомогательных методов)

### Типы сущностей (сервисов)

В API два типа сервисов:

**BL (Business Logic)** — полноценный CRUD для документов/объектов:
- `GET /ServiceCode` — описание сервиса
- `POST /ServiceCode` — создать новую запись (без шаблона)
- `GET /ServiceCode/{pk}` — получить одну запись по первичному ключу
- `POST /ServiceCode/{pk}` — редактировать запись
- `DELETE /ServiceCode/{pk}` — удалить запись
- `GET /ServiceCode/{pk}/title` — название записи
- `GET /ServiceCode/template` — список шаблонов для создания
- `GET /ServiceCode/template/{pk}` — получить шаблон
- `POST /ServiceCode/template/{pk}` — создать запись из шаблона
- `GET /ServiceCode/{pk}/print` — список доступных отчётов
- `GET /ServiceCode/{pk}/attachments` — вложения
- `OPTIONS /ServiceCode` — подробное описание сервиса (WADL)

**SL (Select List)** — списковые/справочные, только чтение + синхронизация:
- `GET /ServiceCode` — описание + опция `hierarchy`
- `GET /ServiceCode/query` — запрос данных с фильтрами
- `GET /ServiceCode/default` — запрос данных с последним использованным видом из Horizon
- `GET /ServiceCode/criteria` — доступные критерии фильтрации
- `GET /ServiceCode/view` — настроенные виды (representations)
- Sync-эндпоинты (см. ниже)

### Параметры запросов для SL (списочных сервисов)

| Параметр | Тип | Описание |
|---|---|---|
| `hierarchy` | boolean | Иерархическая структура ответа (true по умолчанию) |
| `criteria` | string | Критерии выборки (готовые фильтры) |
| `filter` | string | Условия фильтрации по полям данных |
| `columns` | string | Запрашиваемые колонки |
| `optcols` | string | Дополнительные колонки |
| `orderby` | string | Условия сортировки |
| `limit` | al:limittype | Ограничение количества записей |
| `FILTERBY_PK` | integer | Фильтр по первичному ключу |

Пример запроса списка показаний:
```http
GET /API/rest/TdmPNSSkaLigRadSL/query?filter=...&limit=100&hierarchy=false HTTP/1.1
Authorization: Basic dXNlcjpwYXNz
Accept: application/json
```

### Синхронизационные (sync) эндпоинты — очень важно для интеграции!

Для SL-сервисов доступны эндпоинты синхронизации:

```
GET  /ServiceCode/sync              → список ресурсов синхронизации
DELETE /ServiceCode/sync            → очистить историю синхронизации

GET  /ServiceCode/sync/new          → получить новые записи (с момента последней синхр.)
POST /ServiceCode/sync/new          → пометить новые как обработанные

GET  /ServiceCode/sync/edited       → получить изменённые записи
POST /ServiceCode/sync/edited       → пометить изменённые как обработанные

GET  /ServiceCode/sync/changed      → новые + изменённые записи
POST /ServiceCode/sync/changed      → пометить как обработанные

GET  /ServiceCode/sync/deleted      → удалённые записи
POST /ServiceCode/sync/deleted      → пометить удалённые как обработанные
```

Этот механизм — **ключевой для интеграции**: позволяет инкрементально подтягивать изменения без полной перегрузки.

### Схемы данных (XSD)

Каждый сервис предоставляет XSD-схему полей:
```
GET /API/rest/{ServiceCode}/{ServiceCode}.xsd  → XSD-схема полей (требует аутентификации)
GET /API/rest/{ServiceCode}/{ServiceCode}.wadl → WADL-описание сервиса
```

### Отчёты

```
GET /API/rest/{ServiceCode}/print/{reportType}/{param1}/{param2}
```
Возвращает PDF, HTML, Excel:
- `rtQRFastRep/1/0` → PDF/HTML отчёт
- `rtExcelRep/0/0` → Excel отчёт

### Особые системные методы (у всех BL-сервисов)

| Метод | Эндпоинт | Описание |
|---|---|---|
| POST | `/{Code}/AllowedRight` | Проверка прав пользователя (params: `sRight`) |
| POST | `/{Code}/ReadUserParam` | Чтение пользовательского параметра среды (params: `sKods`) |
| POST | `/{Code}/getSLName` | Получить SL-сущность по ID (params: `key`) |
| POST | `/{Code}/doRegisterBLEvent` | Зарегистрировать событие в журнале (params: `DocPk`, `Evnt`, `Text`, `Kods`) |
| POST | `/{Code}/GetUzskValPk` | PK валюты учёта на дату (params: `dtWhen`) |
| POST | `/{Code}/GetReferenceRateFactor` | Множитель конвертации валюты (params: `dtWhen`, `pkValFrom`, `pkValTo`) |
| POST | `/{Code}/ReadSelectList` | Имя соответствующего SL-сервиса |
| POST | `/{Code}/ReadAttachmentList` | Имена SL-сервисов вложений |

---

## 4. Ключевые эндпоинты для учёта счётчиков и ЖКХ-биллинга

### Структура модулей

Система разделена на **два взаимосвязанных модуля**:

- **KNS** (Komunālo Norēķinu Sistēma) — более старый модуль коммунальных расчётов (`TdmKN*` сервисы)
- **NĪP** (Nekustamo Īpašumu Pārvaldība) — модуль управления недвижимостью (`TdmPNS*` сервисы). Более новый, содержит более полный набор сущностей.

Оба модуля находятся в группе **"Nekustamo īpašumu pārvaldība"** (Управление недвижимостью) ServiceTree.

---

### 4.1. Клиенты / Абоненты

#### `TdmKN8ConsBL` — Patērētājs (Потребитель KNS)
**Endpoint**: `GET/POST /API/rest/TdmKN8ConsBL`

| Метод | Путь | Описание |
|---|---|---|
| GET | `/TdmKN8ConsBL` | Описание сервиса |
| POST | `/TdmKN8ConsBL` | Создать нового потребителя |
| GET | `/TdmKN8ConsBL/{pk}` | Получить потребителя по ID |
| POST | `/TdmKN8ConsBL/{pk}` | Редактировать потребителя |
| DELETE | `/TdmKN8ConsBL/{pk}` | Удалить потребителя |
| GET | `/TdmKN8ConsBL/{pk}/title` | Имя/название потребителя |

OpenAPI spec: `/_/API/HorRest/Services/TdmKN8ConsBL/Json`
Демо-документация: `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmKN8ConsBL`

#### `TdmPNSKlientsBL` — NĪP Abonents (Абонент НИП)
**Endpoint**: `GET/POST /API/rest/TdmPNSKlientsBL`

| Метод | Путь | Описание |
|---|---|---|
| POST | `/TdmPNSKlientsBL` | Создать абонента |
| GET | `/TdmPNSKlientsBL/{pk}` | Получить абонента |
| POST | `/TdmPNSKlientsBL/{pk}` | Редактировать абонента |
| DELETE | `/TdmPNSKlientsBL/{pk}` | Удалить абонента |
| POST | `/TdmPNSKlientsBL/ChangePNSKlType` | Изменить тип клиента (params: `pkKlients`, `pkDokt`) |

Вложения: поддерживаются (схема `TdmCustomerAttachmentSL.xsd`)
OpenAPI spec: `/_/API/HorRest/Services/TdmPNSKlientsBL/Json`

#### `TdmPNSKlientsAllBL` — NĪP klients (Клиент НИП, полная версия)
**Endpoint**: `/API/rest/TdmPNSKlientsAllBL`

#### `TDdmNiKlSar` — Klienti (Список клиентов)
**Endpoint**: `/API/rest/TDdmNiKlSar`

---

### 4.2. Договоры / Соглашения

#### `TdmPNSLigBL` — NĪP Līgums (Договор НИП)
**Endpoint**: `/API/rest/TdmPNSLigBL`

Полный CRUD. Специфические подтипы договоров:
- `TdmPNSLigTGDzBL` — Договор аренды жилых помещений (`/API/rest/TdmPNSLigTGDzBL`)
- `TdmPNSLigTGNeBL` — Договор аренды нежилых помещений
- `TdmPNSLigTGSocBL` — Договор социального жилья
- `TdmPNSLigTGApsBL` — Договор управления/хозяйствования
- `TdmPNSLigZemeBL` — Договор аренды земли
- `TdmPNSLigP2BL` — Договор НИП (общий)
- `TdmPNSLigP2KomplBL` — Комплексный договор

#### `TdmPNSWEBClientContractsSL` — NĪP Līgumi (Список договоров)
**Endpoint**: `/API/rest/TdmPNSWEBClientContractsSL`
Список + sync-эндпоинты.

---

### 4.3. Объекты / Помещения / Квартиры

#### `TdmPNSTGBL` — Telpu grupa (Группа помещений / квартира)
**Endpoint**: `/API/rest/TdmPNSTGBL`

Полный CRUD для квартиры/помещения.

#### `TdmPNSObjBL` — Nekustamā īpašuma objekts (Объект недвижимости)
**Endpoint**: `/API/rest/TdmPNSObjBL`

#### `TdmPNSBuveBL` — Būve (ēka) (Здание)
**Endpoint**: `/API/rest/TdmPNSBuveBL`

#### `TdmPNSPerKontsBL` — Personas konts (Лицевой счёт)
**Endpoint**: `/API/rest/TdmPNSPerKontsBL`

#### `TdmPNSPerKonObjBL` — Personas konta objekts (Объект лицевого счёта)
**Endpoint**: `/API/rest/TdmPNSPerKonObjBL`

---

### 4.4. Счётчики

#### `TdmKNSkaBL` — Skaitītājs (KNS) — Счётчик в модуле KNS
**Endpoint**: `/API/rest/TdmKNSkaBL`
OpenAPI spec: `/_/API/HorRest/Services/TdmKNSkaBL/Json`

| Метод | Путь | Описание |
|---|---|---|
| GET | `/TdmKNSkaBL` | Описание сервиса |
| POST | `/TdmKNSkaBL` | Создать счётчик |
| GET | `/TdmKNSkaBL/{pk}` | Получить счётчик по ID (primārā atslēga) |
| POST | `/TdmKNSkaBL/{pk}` | Редактировать счётчик |
| DELETE | `/TdmKNSkaBL/{pk}` | Удалить счётчик |
| GET | `/TdmKNSkaBL/template` | Шаблоны создания |
| POST | `/TdmKNSkaBL/template/{pk}` | Создать по шаблону |
| GET | `/TdmKNSkaBL/{pk}/print` | Доступные отчёты |
| GET | `/TdmKNSkaBL/TdmKNSkaBL.xsd` | XSD-схема полей |
| GET | `/TdmKNSkaBL/TdmKNSkaBL.wadl` | WADL-описание |

#### `TdmKNMajaBL` — Mājas kontrolskaitītāji (Домовые контрольные счётчики)
**Endpoint**: `/API/rest/TdmKNMajaBL`
OpenAPI spec: `/_/API/HorRest/Services/TdmKNMajaBL/Json`

Полный CRUD, аналогичная структура.

#### `TdmPNSSkaBL` — Skaitītājs (NĪP) — Счётчик в модуле НИП
**Endpoint**: `/API/rest/TdmPNSSkaBL`
OpenAPI spec: `/_/API/HorRest/Services/TdmPNSSkaBL/Json`

Полный CRUD + поддержка вложений (схема `TdmPNSSkaAttachmentSL.xsd`).

#### `TdmPNSFuncObjSkaBL` — Funkcionālā objekta skaitītājs (Счётчик функционального объекта)
**Endpoint**: `/API/rest/TdmPNSFuncObjSkaBL`

Полный CRUD + вложения.

#### Справочники для счётчиков (SL):

| Код сервиса | Название | Endpoint |
|---|---|---|
| `TdmKNSkaTipsBL` | KNS Skaitītāja veids (Тип счётчика KNS) | `/API/rest/TdmKNSkaTipsBL` |
| `TdmKNSkaTipsSL` | KNS Skaitītāja veidi (Типы счётчиков, список) | `/API/rest/TdmKNSkaTipsSL` |
| `TdmPNSSkaEksSL` | Skaitītāju eksemplāri (Экземпляры счётчиков) | `/API/rest/TdmPNSSkaEksSL` |
| `TdmPNSSkaEksSkaSL` | Skaitītāju eksemplāri (другой вариант) | `/API/rest/TdmPNSSkaEksSkaSL` |
| `TdmPNSSkaEksMarSL` | Skaitītāja eksemplāra markas (Марки счётчиков) | `/API/rest/TdmPNSSkaEksMarSL` |
| `TdmKNSkatrvBL` | KNS Atrašanās vieta (Место установки счётчика) | `/API/rest/TdmKNSkatrvBL` |
| `TdmPNSKontrolSkaSL` | Kontrolskaitītāji (Контрольные счётчики) | `/API/rest/TdmPNSKontrolSkaSL` |
| `TdmPNSFuncObjSkaSL` | Funkcionālo objektu skaitītāji (Список) | `/API/rest/TdmPNSFuncObjSkaSL` |
| `TdmPNSFuncObjSkaEksSL` | Funkcionālo objektu skaitītāju eksemplāri | `/API/rest/TdmPNSFuncObjSkaEksSL` |
| `TdmPNSDatAvSL` | Rādījumu datu avoti (Источники данных показаний) | `/API/rest/TdmPNSDatAvSL` |

---

### 4.5. Показания счётчиков — КЛЮЧЕВЫЕ ЭНДПОИНТЫ

#### `TdmPNSSkaLigRadSL` — Līgumu skaitītāju rādījumi (**Показания счётчиков по договорам**)
**Endpoint**: `/API/rest/TdmPNSSkaLigRadSL`
OpenAPI spec: `/_/API/HorRest/Services/TdmPNSSkaLigRadSL/Json`
Тип: **SL** (список с расширенными возможностями)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/TdmPNSSkaLigRadSL` | Описание сервиса |
| GET | `/TdmPNSSkaLigRadSL/query` | Запрос показаний с фильтрами |
| GET | `/TdmPNSSkaLigRadSL/default` | Показания с последним Horizon-видом |
| GET | `/TdmPNSSkaLigRadSL/criteria` | Доступные критерии фильтрации |
| GET | `/TdmPNSSkaLigRadSL/view` | Настроенные виды |
| GET | `/TdmPNSSkaLigRadSL/sync/new` | Новые показания (с момента синхр.) |
| POST | `/TdmPNSSkaLigRadSL/sync/new` | Пометить как обработанные |
| GET | `/TdmPNSSkaLigRadSL/sync/edited` | Изменённые показания |
| GET | `/TdmPNSSkaLigRadSL/sync/changed` | Новые + изменённые |
| GET | `/TdmPNSSkaLigRadSL/sync/deleted` | Удалённые показания |
| GET | `/TdmPNSSkaLigRadSL/print/rtQRFastRep/1/0` | PDF-отчёт |
| GET | `/TdmPNSSkaLigRadSL/print/rtExcelRep/0/0` | Excel-отчёт |

#### `TdmPNSSkaNolRadSL` — Nolasītie rādījumi (**Считанные показания**)
**Endpoint**: `/API/rest/TdmPNSSkaNolRadSL`
OpenAPI spec: `/_/API/HorRest/Services/TdmPNSSkaNolRadSL/Json`
Тип: **SL**

Идентичная структура с `TdmPNSSkaLigRadSL` — те же методы query/default/sync/print.

#### `TdmPNSSkaLigSakRadSL` — Skaitītāju sākuma rādījumi (**Начальные показания счётчиков**)
**Endpoint**: `/API/rest/TdmPNSSkaLigSakRadSL`
OpenAPI spec: `/_/API/HorRest/Services/TdmPNSSkaLigSakRadSL/Json`
Тип: **SL**

Идентичная структура — query/default/sync/print.

---

### 4.6. Акты по счётчикам

#### `TdmPNSPnaSkaIzmBL` — Skaitītāju izmaiņu akts (Акт замены счётчиков)
**Endpoint**: `/API/rest/TdmPNSPnaSkaIzmBL`
Тип: **BL** — полный CRUD

#### `TdmPNSPnaSkaBL` — Skaitītāju pārbaudes akts (Акт проверки счётчиков)
**Endpoint**: `/API/rest/TdmPNSPnaSkaBL`
Тип: **BL** — полный CRUD

---

### 4.7. Счета / Рекламации (NĪP Rēķins)

#### `TdmPNSRekBL` — NĪP Rēķins (**Счёт/Рекламация НИП**)
**Endpoint**: `/API/rest/TdmPNSRekBL`
OpenAPI spec: `/_/API/HorRest/Services/TdmPNSRekBL/Json`
Тип: **BL** — полный CRUD + специальные методы

| Метод | Путь | Параметры | Описание |
|---|---|---|---|
| GET | `/TdmPNSRekBL` | — | Описание |
| POST | `/TdmPNSRekBL` | тело документа | Создать счёт |
| GET | `/TdmPNSRekBL/{pk}` | pk: integer | Получить счёт |
| POST | `/TdmPNSRekBL/{pk}` | тело | Редактировать счёт |
| DELETE | `/TdmPNSRekBL/{pk}` | pk | Удалить счёт |
| POST | `/TdmPNSRekBL/{pk}/print/rtQRRepDoc/1/0` | pk | PDF-копия счёта |
| POST | `/TdmPNSRekBL/ExecuteFromKey` | `aKey`, `CounterVal`, `GramDate` | **Провести счёт** |
| POST | `/TdmPNSRekBL/DeExecuteFromKey` | `aKey`, `counterVal` | **Отменить проведение** |
| POST | `/TdmPNSRekBL/BookFromKey` | `aKey`, `CounterVal`, `aSchemaPk`, `DeleteDraft` | **Заверить/отправить в бухгалтерию** |
| POST | `/TdmPNSRekBL/DeBookFromKey` | `aKey`, `counterVal` | **Отменить заверение** |
| POST | `/TdmPNSRekBL/apmaksatFromKey` | `aPkDok`, `aPkSaistDok`, `aSumma`, `aPkVal` | **Оплатить счёт** |
| POST | `/TdmPNSRekBL/prieksApmaksatFromKey` | `aPkDok`, `aPkSaistDok`, `aSumma` | **Предоплата** |
| POST | `/TdmPNSRekBL/ChangeApritStatuss` | `pk`, `AprStPK` | Изменить статус |
| POST | `/TdmPNSRekBL/EditPVNSum` | `aKey`, `aRowPk`, `aPVNSumma` | Изменить сумму НДС |
| POST | `/TdmPNSRekBL/DeleteLink` | `aPkDoc`, `aPkLinkDoc` | Удалить связь документов |
| POST | `/TdmPNSRekBL/LinkDocAutomatically` | `APkDoc`, `ALinkMethod` | Автоматически связать документ |

---

### 4.8. Услуги и тарифы

| Код сервиса | Название | Endpoint |
|---|---|---|
| `TdmPNSPakSL` | NĪP Pakalpojumi (Услуги НИП) | `/API/rest/TdmPNSPakSL` |
| `TdmKNTarifSL` | Tarifi (Тарифы KNS) | `/API/rest/TdmKNTarifSL` |
| `TdmKNTarifShBL` | Tarifa shēma (Схема тарифов) | `/API/rest/TdmKNTarifShBL` |
| `TdmPNSTarLikmeSL` | Tarifu likmes (Ставки тарифов) | `/API/rest/TdmPNSTarLikmeSL` |
| `TdmPNSTarLikmeRSL` | Tarifu likmes (другой вариант) | `/API/rest/TdmPNSTarLikmeRSL` |
| `TdmKNDsctSL` | Atlaides (Скидки) | `/API/rest/TdmKNDsctSL` |
| `TdmKNDsctShBL` | Atlaides shēma (Схема скидок) | `/API/rest/TdmKNDsctShBL` |

---

### 4.9. Дополнительные полезные сущности

| Код | Название | Endpoint | Тип |
|---|---|---|---|
| `TdmKNIedzBL` | Iedzīvotājs (Житель/проживающий KNS) | `/API/rest/TdmKNIedzBL` | BL |
| `TdmKNNormaBL` | Norma (Норматив потребления) | `/API/rest/TdmKNNormaBL` | BL |
| `TdmKNOperBL` | Operators (Оператор KNS) | `/API/rest/TdmKNOperBL` | BL |
| `TdmKNConsGrpBL` | Patērētāja grupa (Группа потребителей) | `/API/rest/TdmKNConsGrpBL` | BL |
| `TdmKNBindcBL` | Patēriņa kods (Код потребления) | `/API/rest/TdmKNBindcBL` | BL |
| `TdmKNVariableBL` | KNS Mainīgais (Переменная KNS) | `/API/rest/TdmKNVariableBL` | BL |
| `TdmPNSObjVarRSL` | Mājas aprēķinu pārskats (Отчёт расчётов дома) | `/API/rest/TdmPNSObjVarRSL` | SL |
| `TdmPNSPaterUzskSL` | Objektu patēriņa uzskaite (Учёт потребления объектов) | `/API/rest/TdmPNSPaterUzskSL` | SL |
| `TdmPNSApjAprRindSL` | Apjoma aprēķina rindas (Строки расчёта объёмов) | `/API/rest/TdmPNSApjAprRindSL` | SL |
| `TdmPNSBillingObjSL` | Nekustamā īpašuma objekts (Биллинг объект) | `/API/rest/TdmPNSBillingObjSL` | SL |
| `TPNSpvzRndSar` | Pavadzīmju un rēķinu rindas (Строки накладных и счетов) | `/API/rest/TPNSpvzRndSar` | SL |
| `TdmPNSPiesSL` | Pieslēgumi (Подключения) | `/API/rest/TdmPNSPiesSL` | SL |
| `TdmKNAdrSL` | KNS Adreses (Адреса KNS) | `/API/rest/TdmKNAdrSL` | SL |
| `TdmKN8IedzSL` | KNS Iedzīvotāji (Список жителей KNS) | `/API/rest/TdmKN8IedzSL` | SL |
| `TdmKNSvcplBL` | KNS Servisa plāns (Сервисный план KNS) | `/API/rest/TdmKNSvcplBL` | BL |
| `TdmPNSNIPRegisterSL` | NĪP WEB lietotāju reģistrācija (Регистрация WEB-пользователей НИП) | `/API/rest/TdmPNSNIPRegisterSL` | SL |

---

## 5. Как создать / получить показания счётчиков

### Получение списка счётчиков для объекта/договора

Поскольку `TdmPNSSkaLigRadSL` (показания по договорам) — это SL, получить показания можно через:

```http
GET /API/rest/TdmPNSSkaLigRadSL/query?hierarchy=false&filter=<условие_по_договору>&limit=100
Authorization: Basic dXNlcjpwYXNz
Accept: application/json
```

Или получить XSD для понимания полей:
```http
GET /API/rest/TdmPNSSkaLigRadSL/TdmPNSSkaLigRadSL.xsd
Authorization: Basic dXNlcjpwYXNz
Accept: application/xml
```

Для счётчика NĪP (`TdmPNSSkaBL`):
```http
GET /API/rest/TdmPNSSkaBL/{pk}
Authorization: Basic dXNlcjpwYXNz
Accept: application/json
```

### Создание показания счётчика

`TdmPNSSkaLigRadSL` и `TdmPNSSkaNolRadSL` — это **SL** (только чтение/синхронизация). Показания **нельзя напрямую записать** через эти сервисы.

Запись показаний вероятно производится через **акт `TdmPNSPnaSkaIzmBL`** (Akts izmaiņu skaitītājiem) — это BL с полным CRUD:

```http
POST /API/rest/TdmPNSPnaSkaIzmBL
Authorization: Basic dXNlcjpwYXNz
Content-Type: application/json
Accept: application/json

{
  // поля акта — структуру см. через OPTIONS /API/rest/TdmPNSPnaSkaIzmBL
  // или через GET /API/rest/TdmPNSPnaSkaIzmBL/TdmPNSPnaSkaIzmBL.xsd
}
```

Или через шаблон:
```http
GET /API/rest/TdmPNSPnaSkaIzmBL/template
Authorization: Basic dXNlcjpwYXNz
Accept: application/json

# → список шаблонов

GET /API/rest/TdmPNSPnaSkaIzmBL/template/{pk}
# → шаблон с заполненными полями по умолчанию

POST /API/rest/TdmPNSPnaSkaIzmBL/template/{pk}
Content-Type: application/json

{
  // данные нового показания на основе шаблона
}
```

Для понимания структуры данных крайне важно получить XSD-схемы (требуют аутентификации):
```http
GET /API/rest/TdmPNSPnaSkaIzmBL/TdmPNSPnaSkaIzmBL.xsd
Authorization: Basic dXNlcjpwYXNz
```

### Цикл интеграции (рекомендуемый)

1. **Инициализация**: Получить список договоров через `TdmPNSWEBClientContractsSL/query`
2. **Получить счётчики**: `TdmPNSSkaBL/query` или `TdmKNSkaBL/query`
3. **Показания**: `TdmPNSSkaLigRadSL/query` с фильтром по договору/счётчику
4. **Новые показания с момента синхр.**: `TdmPNSSkaLigRadSL/sync/new`
5. **Записать показания**: `POST /TdmPNSPnaSkaIzmBL/template/{pk}` с данными
6. **Создать счёт**: `POST /TdmPNSRekBL` → `POST /TdmPNSRekBL/ExecuteFromKey`

---

## 6. Лимиты, формат ошибок, sandbox

### Лимиты запросов

Документация **не содержит явного упоминания rate-limit**. Поскольку это on-premise система, лимиты определяются мощностью сервера клиента. Параметр `limit` в query-запросах позволяет контролировать количество возвращаемых записей.

### Формат ошибок

Эндпоинт `/_/API/restAuth` возвращает:
- `405 Method Not Allowed` на GET-запросы (только POST)
- `401 Unauthorized` при неверных учётных данных (XSD-схемы требуют аутентификации — подтверждено при попытке `/_/API/rest/TdmKNSkaBL/TdmKNSkaBL.xsd` → `401`)

Стандартные HTTP-коды:
- `200` — успех
- `401` — не аутентифицирован
- `404` — ресурс не найден

### Sandbox / тестовая среда

**Отдельной публичной sandbox-среды нет.** Документационный сайт `horizon-rest-doc.visma.lv` сам по себе является демо-документацией. UI позволяет исполнять запросы (кнопка Execute), но только после аутентификации через логин/пароль. Для разработки нужно запрашивать у Visma Latvia тестовый доступ к экземпляру Horizon.

---

## 7. SDK, примеры кода

### SDK

**Официального SDK нет** — ни клиентских библиотек, ни npm/NuGet пакетов в открытом доступе не обнаружено.

### Код, доступный из документационного сайта

JavaScript-код UI документации раскрывает паттерн интеграции:

**Аутентификация (из `api-doc.7c0105fa.js`):**
```javascript
// POST на /_/API/restAuth
const response = await fetch("/_/API/restAuth", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({Login: username, Password: password})
});
// При успехе строим Basic auth header:
const authHeader = "Basic " + btoa(username + ":" + password);
```

**Выполнение REST-запросов:**
```javascript
const url = new URL("/_/API/rest" + pathKey, window.location.href);
// path params: url.pathname = url.pathname.replace("%7Bname%7D", value)
// query params: url.searchParams.append(name, value)
// headers: {"Authorization": authHeader, "Accept": acceptContentType}
const response = await fetch(url.toString(), {
  method: httpMethod,
  headers: headers,
  body: requestBody  // для POST/PUT
});
```

### Получение полных OpenAPI JSON-спецификаций

```bash
curl -u "login:password" \
  "https://horizon-server/API/rest/TdmKNSkaBL/TdmKNSkaBL.xsd" \
  -H "Accept: application/xml"

curl "https://horizon-rest-doc.visma.lv/_/API/HorRest/Services/TdmPNSSkaLigRadSL/Json" \
  -H "Accept: application/json"
```

---

## Использованные URLs документации

| URL | Содержимое |
|---|---|
| `https://horizon-rest-doc.visma.lv/lv` | Главная страница SPA |
| `https://horizon-rest-doc.visma.lv/_/API/ServiceTree` | **Полный список сервисов (JSON)** |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/global` | Системные ресурсы без аутентификации |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmKNSkaBL` | Счётчик KNS |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmKNMajaBL` | Домовые счётчики KNS |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmKN8ConsBL` | Потребитель KNS |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmPNSSkaBL` | Счётчик NĪP |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmPNSSkaLigRadSL` | Показания счётчиков по договорам |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmPNSSkaNolRadSL` | Считанные показания |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmPNSSkaLigSakRadSL` | Начальные показания |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmPNSRekBL` | Счёт/Рекламация НИП |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmPNSKlientsBL` | Абонент НИП |
| `https://horizon-rest-doc.visma.lv/_/API/OpenApi/OpenApiUIModel/TdmPNSFuncObjSkaBL` | Счётчик функц. объекта |
| `https://horizon-rest-doc.visma.lv/js/app.3f38456b.js` | Логика аутентификации |
| `https://horizon-rest-doc.visma.lv/js/api-doc.7c0105fa.js` | Логика выполнения API-запросов |

---

## Пробелы и неопределённости

1. **Конкретные JSON/XML поля** (`pk`, `Datums`, `Radijums`, `SkatPk` и т.д.) не раскрыты в OpenAPI spec без аутентификации — схемы доступны только через `/{Code}.xsd` после логина. Для их получения нужен реальный доступ к Horizon-серверу.

2. **Запись показаний**: Неочевидно, какой именно BL-сервис принимает новые показания и какова точная структура запроса. Предположительно `TdmPNSPnaSkaIzmBL` или `TdmKNSkaBL` с записью в связанные поля. Требуется уточнение у разработчиков или изучение XSD-схем.

3. **Параметры фильтрации** (`filter=`, `criteria=`): Синтаксис фильтров не задокументирован публично. Для понимания нужно выполнить `GET /TdmPNSSkaLigRadSL/criteria` (возвращает список доступных критериев) и `OPTIONS /TdmPNSSkaLigRadSL` (WADL).

4. **Пагинация**: Параметр `limit` есть, но механизм курсора/offset не задокументирован в публично доступной части.

5. **Реальный базовый URL клиента**: Каждый клиент имеет свой сервер — нужно уточнять у Visma Latvia или конкретного клиента-оператора.

6. **Версионирование**: API версия 620.4 соответствует версии самой системы Horizon. Изменения API между версиями отслеживаются через Delta-раздел документационного портала (`/lv/Delta`).