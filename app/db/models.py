from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, Text, func
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

    manager: Mapped[User | None] = relationship()


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
