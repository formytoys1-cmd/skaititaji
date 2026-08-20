"""Модель данных платформы.

Ключевые идеи архитектуры:
- **Мультиарендность (multi-tenant):** всё привязано к `Organization` (арендатор —
  управляющий/кооператив/водовод). Разные организации изолированы данными.
- **Config-driven типы счётчиков:** `MeterType` — это данные, а не код. Добавление
  нового типа счётчика = новая строка в каталоге, без изменения логики подачи.
- **Расширяемость:** дополнительные атрибуты хранятся в JSON-полях (`extra`),
  что позволяет дорабатывать формы без миграций схемы.
"""
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.utcnow()


# --------------------------------------------------------------------------- #
# Перечисления
# --------------------------------------------------------------------------- #
class UserRole(str, Enum):
    SUPERADMIN = "superadmin"   # владелец платформы
    MANAGER = "manager"         # apsaimniekotājs / администратор организации
    RESIDENT = "resident"       # житель / собственник


class ReadingSource(str, Enum):
    WEB = "web"                 # подано через сайт жителем
    MANAGER = "manager"         # внесено управляющим
    IMPORT = "import"           # импортировано
    ESTIMATED = "estimated"     # расчётное (норма) при отсутствии показаний
    METER_OPERATOR = "operator" # снято обходчиком


class ReadingStatus(str, Enum):
    SUBMITTED = "submitted"     # подано
    ACCEPTED = "accepted"       # принято управляющим
    SYNCED = "synced"           # выгружено в учётную систему (Visma Horizon)
    REJECTED = "rejected"       # отклонено (аномалия)


class MeterCategory(str, Enum):
    WATER = "water"
    ENERGY = "energy"
    GAS = "gas"
    HEAT = "heat"
    OTHER = "other"


class FeedbackStatus(str, Enum):
    """Статус треда обратной связи (указания модератора агенту)."""
    NEW = "new"                       # подано, агент ещё не видел
    IN_PROGRESS = "in_progress"       # агент взял в работу
    NEEDS_CLARIFICATION = "needs_clarification"  # агент ждёт уточнения
    READY_FOR_REVIEW = "ready_for_review"        # сделано, на проверке
    DONE = "done"                     # модератор принял
    REJECTED = "rejected"             # модератор отклонил/отменил


class FeedbackScope(str, Enum):
    FULL = "full"          # полная переделка
    PARTIAL = "partial"    # частичная доработка
    BUG = "bug"            # исправить ошибку
    IDEA = "idea"          # идея/предложение


class FeedbackAuthor(str, Enum):
    MODERATOR = "moderator"
    AGENT = "agent"


# --------------------------------------------------------------------------- #
# Арендатор (организация)
# --------------------------------------------------------------------------- #
class Organization(SQLModel, table=True):
    __tablename__ = "organization"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)          # для URL: /o/{slug}
    name: str
    legal_name: Optional[str] = None
    reg_number: Optional[str] = None                    # реģ. номер предприятия
    kind: str = Field(default="manager")                # manager | cooperative | utility
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    # Брендинг демо-страниц организации
    brand_color: str = Field(default="#0369a1")
    logo_text: Optional[str] = None

    # Окно подачи показаний (дни месяца)
    reading_day_from: int = Field(default=25)
    reading_day_to: int = Field(default=5)              # до 5 числа след. месяца

    # Настройки интеграции с учётной системой
    integration_provider: str = Field(default="visma_horizon")
    integration_config: dict = Field(default_factory=dict, sa_column=Column(JSON))

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

    buildings: list["Building"] = Relationship(back_populates="organization")
    users: list["User"] = Relationship(back_populates="organization")


# --------------------------------------------------------------------------- #
# Каталог типов счётчиков (config-driven)
# --------------------------------------------------------------------------- #
class MeterType(SQLModel, table=True):
    """Тип счётчика. Глобальный каталог; организация может включать нужные типы.

    Добавление нового типа счётчика (например, «электроэнергия», «газ»,
    «тепло») — это просто новая запись здесь, никакого нового кода не требуется.
    """
    __tablename__ = "meter_type"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)          # cold_water, hot_water, ...
    category: MeterCategory = Field(default=MeterCategory.WATER)

    name_lv: str
    name_ru: str
    name_en: str

    unit: str = Field(default="m³")                     # единица измерения
    decimals: int = Field(default=3)                    # знаков после запятой
    icon: str = Field(default="💧")
    color: str = Field(default="#0ea5e9")
    sort_order: int = Field(default=100)

    # Правила валидации подачи
    max_plausible_consumption: float = Field(default=100.0)  # аномалия, если больше
    allow_zero_consumption: bool = Field(default=True)

    # Произвольная схема доп. полей (JSON), позволяет расширять форму
    field_schema: dict = Field(default_factory=dict, sa_column=Column(JSON))

    is_active: bool = Field(default=True)


# --------------------------------------------------------------------------- #
# Объекты недвижимости
# --------------------------------------------------------------------------- #
class Building(SQLModel, table=True):
    __tablename__ = "building"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id", index=True)
    name: Optional[str] = None
    address: str
    external_id: Optional[str] = None                   # id объекта в учётной системе

    organization: Optional[Organization] = Relationship(back_populates="buildings")
    units: list["Unit"] = Relationship(back_populates="building")


class Unit(SQLModel, table=True):
    """Квартира / помещение (dzīvoklis / telpa)."""
    __tablename__ = "unit"

    id: Optional[int] = Field(default=None, primary_key=True)
    building_id: int = Field(foreign_key="building.id", index=True)
    number: str                                         # номер квартиры
    account_number: Optional[str] = None                # лицевой счёт / klienta konts
    area_m2: Optional[float] = None
    residents_count: Optional[int] = None
    external_id: Optional[str] = None

    building: Optional[Building] = Relationship(back_populates="units")
    meters: list["Meter"] = Relationship(back_populates="unit")


# --------------------------------------------------------------------------- #
# Пользователи
# --------------------------------------------------------------------------- #
class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: Optional[int] = Field(
        default=None, foreign_key="organization.id", index=True
    )
    email: str = Field(index=True)
    full_name: str
    password_hash: str
    role: UserRole = Field(default=UserRole.RESIDENT)
    phone: Optional[str] = None
    locale: str = Field(default="lv")
    is_active: bool = Field(default=True)
    # AUTH-001: связь с внешней (eIDAS) личностью. Заполняется, когда житель
    # входит через банк / Smart-ID / eParaksts. Для локального (email+пароль)
    # входа остаются пустыми — обратная совместимость сохранена.
    external_provider: Optional[str] = Field(default=None, index=True)
    external_subject: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)

    organization: Optional[Organization] = Relationship(back_populates="users")


class UnitResident(SQLModel, table=True):
    """Связь житель ↔ квартира (собственник/наниматель может иметь несколько)."""
    __tablename__ = "unit_resident"
    __table_args__ = (UniqueConstraint("user_id", "unit_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    unit_id: int = Field(foreign_key="unit.id", index=True)
    relation: str = Field(default="owner")              # owner | tenant


# --------------------------------------------------------------------------- #
# Счётчики и показания
# --------------------------------------------------------------------------- #
class Meter(SQLModel, table=True):
    __tablename__ = "meter"

    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id", index=True)
    meter_type_id: int = Field(foreign_key="meter_type.id", index=True)

    serial_number: str                                  # заводской номер
    location: Optional[str] = None                      # напр. «санузел»
    initial_value: float = Field(default=0.0)
    installed_on: Optional[date] = None
    verification_due: Optional[date] = None             # поверка до
    external_id: Optional[str] = None                   # id счётчика в учётной системе
    is_active: bool = Field(default=True)

    unit: Optional[Unit] = Relationship(back_populates="meters")
    meter_type: Optional[MeterType] = Relationship()
    readings: list["Reading"] = Relationship(back_populates="meter")


class Reading(SQLModel, table=True):
    __tablename__ = "reading"
    # DATA-002: одно показание на (счётчик, период) — защита от дублей/гонок.
    __table_args__ = (
        UniqueConstraint("meter_id", "period", name="uq_reading_meter_period"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    meter_id: int = Field(foreign_key="meter.id", index=True)
    period: str = Field(index=True)                     # YYYY-MM (расчётный период)
    value: float                                        # показание счётчика
    consumption: Optional[float] = None                 # расход за период
    reading_date: date = Field(default_factory=date.today)

    source: ReadingSource = Field(default=ReadingSource.WEB)
    status: ReadingStatus = Field(default=ReadingStatus.SUBMITTED)
    is_anomaly: bool = Field(default=False)
    note: Optional[str] = None

    submitted_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    synced_at: Optional[datetime] = None
    external_id: Optional[str] = None                   # id показания в учётной системе
    created_at: datetime = Field(default_factory=utcnow)

    meter: Optional[Meter] = Relationship(back_populates="readings")


class IntegrationLog(SQLModel, table=True):
    """Журнал синхронизации с учётной системой (Visma Horizon)."""
    __tablename__ = "integration_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id", index=True)
    provider: str = Field(default="visma_horizon")
    action: str                                         # push_readings, pull_meters...
    status: str                                         # ok | error
    message: Optional[str] = None
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- #
# OPS-001 — журнал аудита действий
# --------------------------------------------------------------------------- #
class AuditLog(SQLModel, table=True):
    """Неизменяемый журнал: кто, что, когда, старое/новое значение.

    Записи создаются на всех mutating-операциях с показаниями и на изменениях
    статусов/ролей. Строки трактуются как append-only: их нельзя изменять или
    удалять (обеспечивается на уровне приложения — записи не редактируются).
    """
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: Optional[int] = Field(
        default=None, foreign_key="user.id", index=True
    )                                                   # кто выполнил действие
    action: str = Field(index=True)                     # reading_submit, reading_status_change...
    entity_type: str = Field(index=True)                # reading | user | ...
    entity_id: Optional[int] = Field(default=None, index=True)
    old_value: dict = Field(default_factory=dict, sa_column=Column(JSON))
    new_value: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)


# --------------------------------------------------------------------------- #
# Обратная связь (консоль модератора → агент)
# --------------------------------------------------------------------------- #
class FeedbackThread(SQLModel, table=True):
    """Тред обратной связи: одно указание модератора и переписка по нему.

    Модератор через веб-консоль создаёт тред с указаниями. Агент (эта запущенная
    сессия) через watcher получает уведомление, берёт в работу, отвечает и ставит
    статус. Если что-то неясно — переводит в NEEDS_CLARIFICATION и пишет вопрос.
    """
    __tablename__ = "feedback_thread"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    scope: FeedbackScope = Field(default=FeedbackScope.PARTIAL)
    priority: str = Field(default="normal")            # low | normal | high
    area: Optional[str] = None                         # какая страница/функция
    status: FeedbackStatus = Field(default=FeedbackStatus.NEW)
    created_by: Optional[str] = None                   # email модератора
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    messages: list["FeedbackMessage"] = Relationship(back_populates="thread")


class FeedbackMessage(SQLModel, table=True):
    """Сообщение в треде: от модератора или от агента."""
    __tablename__ = "feedback_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="feedback_thread.id", index=True)
    author: FeedbackAuthor = Field(default=FeedbackAuthor.MODERATOR)
    body: str
    created_at: datetime = Field(default_factory=utcnow)

    thread: Optional[FeedbackThread] = Relationship(back_populates="messages")


class FeedbackAttachment(SQLModel, table=True):
    """Файл, прикреплённый модератором к треду/сообщению (бумажные формы и т.п.)."""
    __tablename__ = "feedback_attachment"

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="feedback_thread.id", index=True)
    message_id: Optional[int] = Field(default=None, foreign_key="feedback_message.id")
    filename: str                                       # исходное имя файла
    stored_name: str                                    # имя на диске (uuid)
    content_type: Optional[str] = None
    size: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)
