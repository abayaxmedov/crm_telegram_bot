from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    DailyReport,
    Doctor,
    FinanceOperation,
    FinanceType,
    Pharmacy,
    Request,
    RequestStatus,
    Role,
    Salary,
    User,
)


def make_invite_token() -> str:
    return secrets.token_urlsafe(24)


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_invite_token(session: AsyncSession, token: str) -> User | None:
    result = await session.execute(select(User).where(User.invite_token == token))
    return result.scalar_one_or_none()


async def seed_owners(session: AsyncSession, owner_ids: Iterable[int]) -> None:
    for telegram_id in owner_ids:
        user = await get_user_by_telegram_id(session, telegram_id)
        if user is None:
            session.add(
                User(
                    telegram_id=telegram_id,
                    full_name=f"Owner {telegram_id}",
                    role=Role.OWNER,
                    is_active=True,
                    invite_used=True,
                    activated_at=datetime.now(timezone.utc),
                )
            )
            continue

        user.role = Role.OWNER
        user.is_active = True
        user.invite_used = True
        user.activated_at = user.activated_at or datetime.now(timezone.utc)

    await session.commit()


async def create_invited_user(
    session: AsyncSession,
    *,
    role: Role,
    full_name: str,
    created_by: User,
    phone_number: str | None = None,
) -> User:
    user = User(
        full_name=full_name,
        role=role,
        phone_number=phone_number,
        is_active=True,
        invite_token=make_invite_token(),
        invite_used=False,
        invited_by_id=created_by.id,
    )
    session.add(user)
    await session.flush()
    await log_action(session, created_by, "user_invite_created", "user", str(user.id), f"role={role.value}")
    return user


async def bind_invited_user(
    session: AsyncSession,
    *,
    user: User,
    telegram_id: int,
    full_name: str,
    username: str | None,
) -> User:
    user.telegram_id = telegram_id
    user.full_name = user.full_name or full_name
    user.username = username
    user.invite_used = True
    user.activated_at = datetime.now(timezone.utc)
    await log_action(session, user, "invite_activated", "user", str(user.id), f"telegram_id={telegram_id}")
    return user


async def list_users(session: AsyncSession, limit: int = 30) -> list[User]:
    result = await session.execute(select(User).order_by(desc(User.created_at)).limit(limit))
    return list(result.scalars())


async def add_doctor(
    session: AsyncSession,
    *,
    full_name: str,
    phone_number: str | None,
    location_text: str | None,
    class_category: str | None,
    manager: User,
    notes: str | None,
) -> Doctor:
    doctor = Doctor(
        full_name=full_name,
        phone_number=phone_number,
        location_text=location_text,
        class_category=class_category,
        manager_id=manager.id,
        notes=notes,
    )
    session.add(doctor)
    await session.flush()
    await log_action(session, manager, "doctor_created", "doctor", str(doctor.id), full_name)
    return doctor


async def list_doctors(session: AsyncSession, limit: int = 20) -> list[Doctor]:
    result = await session.execute(select(Doctor).order_by(desc(Doctor.created_at)).limit(limit))
    return list(result.scalars())


async def add_pharmacy(
    session: AsyncSession,
    *,
    name: str,
    phone_number: str | None,
    location_text: str | None,
    responsible_person: str | None,
    manager: User,
    notes: str | None,
) -> Pharmacy:
    pharmacy = Pharmacy(
        name=name,
        phone_number=phone_number,
        location_text=location_text,
        responsible_person=responsible_person,
        manager_id=manager.id,
        notes=notes,
    )
    session.add(pharmacy)
    await session.flush()
    await log_action(session, manager, "pharmacy_created", "pharmacy", str(pharmacy.id), name)
    return pharmacy


async def list_pharmacies(session: AsyncSession, limit: int = 20) -> list[Pharmacy]:
    result = await session.execute(select(Pharmacy).order_by(desc(Pharmacy.created_at)).limit(limit))
    return list(result.scalars())


async def add_daily_report(
    session: AsyncSession,
    *,
    author: User,
    target_type: str,
    target_name: str | None,
    text: str | None,
    voice_file_id: str | None,
) -> DailyReport:
    report = DailyReport(
        author_id=author.id,
        target_type=target_type,
        target_name=target_name,
        text=text,
        voice_file_id=voice_file_id,
    )
    session.add(report)
    await session.flush()
    await log_action(session, author, "daily_report_created", "daily_report", str(report.id), target_type)
    return report


async def list_daily_reports(session: AsyncSession, *, actor: User, limit: int = 20) -> list[DailyReport]:
    query = select(DailyReport).order_by(desc(DailyReport.created_at)).limit(limit)
    if actor.role != Role.OWNER:
        query = query.where(DailyReport.author_id == actor.id)

    result = await session.execute(query)
    return list(result.scalars())


async def add_request(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
    created_by: User,
) -> Request:
    request = Request(title=title, description=description, created_by_id=created_by.id)
    session.add(request)
    await session.flush()
    await log_action(session, created_by, "request_created", "request", str(request.id), title)
    return request


async def list_requests(session: AsyncSession, limit: int = 20) -> list[Request]:
    result = await session.execute(select(Request).order_by(desc(Request.created_at)).limit(limit))
    return list(result.scalars())


async def update_request_status(
    session: AsyncSession,
    *,
    request_id: int,
    status: RequestStatus,
    actor: User,
) -> Request | None:
    result = await session.execute(select(Request).where(Request.id == request_id))
    request = result.scalar_one_or_none()
    if request is None:
        return None

    request.status = status
    await log_action(session, actor, "request_status_changed", "request", str(request.id), status.value)
    return request


async def add_finance_operation(
    session: AsyncSession,
    *,
    operation_type: FinanceType,
    amount: Decimal,
    title: str,
    description: str | None,
    created_by: User,
) -> FinanceOperation:
    operation = FinanceOperation(
        operation_type=operation_type,
        amount=amount,
        title=title,
        description=description,
        created_by_id=created_by.id,
    )
    session.add(operation)
    await session.flush()
    await log_action(session, created_by, "finance_operation_created", "finance", str(operation.id), title)
    return operation


async def list_finance_operations(session: AsyncSession, limit: int = 100) -> list[FinanceOperation]:
    result = await session.execute(select(FinanceOperation).order_by(desc(FinanceOperation.created_at)).limit(limit))
    return list(result.scalars())


async def add_salary(
    session: AsyncSession,
    *,
    user: User,
    month: str,
    base_salary: Decimal,
    bonus: Decimal,
    penalty: Decimal,
) -> Salary:
    total = base_salary + bonus - penalty
    salary = Salary(
        user_id=user.id,
        month=month,
        base_salary=base_salary,
        bonus=bonus,
        penalty=penalty,
        total_amount=total,
    )
    session.add(salary)
    await session.flush()
    return salary


async def list_salaries_for_user(session: AsyncSession, user: User, limit: int = 12) -> list[Salary]:
    result = await session.execute(
        select(Salary).where(Salary.user_id == user.id).order_by(desc(Salary.created_at)).limit(limit)
    )
    return list(result.scalars())


async def log_action(
    session: AsyncSession,
    actor: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )

