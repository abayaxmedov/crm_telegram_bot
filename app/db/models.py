from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def enum_type(enum_cls: type[enum.Enum]) -> SqlEnum:
    return SqlEnum(enum_cls, values_callable=lambda values: [item.value for item in values], native_enum=False)


class Role(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"
    OPERATOR = "operator"
    ASSISTANT = "assistant"
    DOCTOR = "doctor"
    PHARMACY = "pharmacy"


class RequestStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELED = "canceled"


class FinanceType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    DEBT = "debt"
    PAYMENT = "payment"


class ContractStatus(str, enum.Enum):
    ACTIVE = "active"
    REQUESTED = "requested"


class WarehouseStatus(str, enum.Enum):
    NEW = "new"
    APPROVED = "approved"
    REJECTED = "rejected"


class RepPaymentKind(str, enum.Enum):
    ISSUE = "issue"      # admin -> medvakil (под отчёт berildi)
    PAYOUT = "payout"    # medvakil -> vrach (bonus to'lovi)
    RETURN = "return"    # medvakil -> admin (qaytarish)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_type(Role), index=True)
    phone_number: Mapped[str | None] = mapped_column(String(64))
    # Tanlangan interfeys tili: "uz_cyrl" yoki "ru". None => hali tanlanmagan.
    language: Mapped[str | None] = mapped_column(String(16))
    # Медвакил (медпредставитель) uchun: region va "под отчёт" balans.
    region_city: Mapped[str | None] = mapped_column(String(120))
    region_rayon: Mapped[str | None] = mapped_column(String(120))
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    invite_token: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    invite_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    invited_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    invited_by: Mapped["User | None"] = relationship(remote_side="User.id")


class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    phone_number: Mapped[str | None] = mapped_column(String(64))
    location_text: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    class_category: Mapped[str | None] = mapped_column(String(120))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    # Sotuvlar orqali to'planadigan, medvakil to'laydigan bonus balansi.
    bonus_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")

    manager: Mapped[User | None] = relationship()


class Pharmacy(Base, TimestampMixin):
    __tablename__ = "pharmacies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    phone_number: Mapped[str | None] = mapped_column(String(64))
    location_text: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    responsible_person: Mapped[str | None] = mapped_column(String(255))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    # ИНН va филиал (test3640bot: "мунавара (Филиал: 1)").
    inn: Mapped[str | None] = mapped_column(String(32), index=True)
    filial: Mapped[str | None] = mapped_column(String(120))

    manager: Mapped[User | None] = relationship()

    contracts: Mapped[list["Contract"]] = relationship(back_populates="pharmacy")


class DailyReport(Base, TimestampMixin):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    target_name: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str | None] = mapped_column(Text)
    voice_file_id: Mapped[str | None] = mapped_column(String(255))

    author: Mapped[User] = relationship()


class Request(Base, TimestampMixin):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(
        enum_type(RequestStatus),
        default=RequestStatus.NEW,
        server_default=RequestStatus.NEW.value,
        index=True,
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    assigned_to: Mapped[User | None] = relationship(foreign_keys=[assigned_to_id])


class Salary(Base, TimestampMixin):
    __tablename__ = "salaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    month: Mapped[str] = mapped_column(String(32), index=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")
    bonus: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")
    penalty: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(32), default="unpaid", server_default="unpaid")

    user: Mapped[User] = relationship()


class FinanceOperation(Base, TimestampMixin):
    __tablename__ = "finance_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_type: Mapped[FinanceType] = mapped_column(enum_type(FinanceType), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    created_by: Mapped[User] = relationship()


class Drug(Base, TimestampMixin):
    """Препарат — sotiladigan dori. Qoldiq, vrach bonus stavkasi va KPI plani bilan."""

    __tablename__ = "drugs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # qoldiq (упак.)
    # Sotilgan har upakovka uchun vrachga hisoblanadigan bonus.
    doctor_bonus_per_pack: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    # KPI (medvakil zarplatasi) uchun: plan (упак.), davr (oy), 100% bajarilganda to'liq bonus.
    kpi_plan_qty: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    kpi_period_months: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    kpi_bonus_full: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Contract(Base, TimestampMixin):
    """Договор — apteka bilan shartnoma (склад заявкаси shu asosda)."""

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("pharmacies.id", ondelete="CASCADE"), index=True)
    number: Mapped[str] = mapped_column(String(120))
    signed_date: Mapped[str | None] = mapped_column(String(32))  # "20.05.2026" ko'rinishida
    status: Mapped[ContractStatus] = mapped_column(
        enum_type(ContractStatus), default=ContractStatus.ACTIVE, server_default=ContractStatus.ACTIVE.value
    )
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    pharmacy: Mapped[Pharmacy] = relationship(back_populates="contracts")


class Sale(Base, TimestampMixin):
    """Продажа/Рецепт — medvakil qayd etgan sotuv (savat)."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    pharmacy_id: Mapped[int | None] = mapped_column(ForeignKey("pharmacies.id", ondelete="SET NULL"))
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id", ondelete="SET NULL"))
    total_bonus: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")

    rep: Mapped[User] = relationship()
    pharmacy: Mapped[Pharmacy | None] = relationship()
    doctor: Mapped[Doctor | None] = relationship()
    items: Mapped[list["SaleItem"]] = relationship(back_populates="sale", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id", ondelete="SET NULL"), index=True)
    drug_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer)
    bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    sale: Mapped[Sale] = relationship(back_populates="items")


class WarehouseRequest(Base, TimestampMixin):
    """Заявка на склад — apteka uchun договор asosida buyurtma."""

    __tablename__ = "warehouse_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    pharmacy_id: Mapped[int | None] = mapped_column(ForeignKey("pharmacies.id", ondelete="SET NULL"))
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id", ondelete="SET NULL"))
    status: Mapped[WarehouseStatus] = mapped_column(
        enum_type(WarehouseStatus), default=WarehouseStatus.NEW, server_default=WarehouseStatus.NEW.value, index=True
    )

    rep: Mapped[User] = relationship()
    pharmacy: Mapped[Pharmacy | None] = relationship()
    contract: Mapped[Contract | None] = relationship()
    items: Mapped[list["WarehouseRequestItem"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class WarehouseRequestItem(Base):
    __tablename__ = "warehouse_request_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("warehouse_requests.id", ondelete="CASCADE"), index=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id", ondelete="SET NULL"))
    drug_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer)

    request: Mapped[WarehouseRequest] = relationship(back_populates="items")


class VisitDiary(Base):
    """Дневник визитов — geolokatsiyaga bog'langan ташриф yozuvi."""

    __tablename__ = "visit_diaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    rep: Mapped[User] = relationship()


class RepPayment(Base):
    """Финанс harakati: под-отчёт berish / vrachga to'lov / adminga qaytarish."""

    __tablename__ = "rep_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id", ondelete="SET NULL"))
    kind: Mapped[RepPaymentKind] = mapped_column(enum_type(RepPaymentKind), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    rep: Mapped[User] = relationship()
    doctor: Mapped[Doctor | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(120))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actor: Mapped[User | None] = relationship()
