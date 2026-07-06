from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AuditLog,
    Contract,
    ContractStatus,
    DailyReport,
    Doctor,
    Drug,
    FinanceOperation,
    FinanceType,
    Pharmacy,
    RepPayment,
    RepPaymentKind,
    Request,
    RequestStatus,
    Role,
    Salary,
    Sale,
    SaleItem,
    User,
    VisitDiary,
    WarehouseRequest,
    WarehouseRequestItem,
    WarehouseStatus,
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
    inn: str | None = None,
    filial: str | None = None,
) -> Pharmacy:
    pharmacy = Pharmacy(
        name=name,
        phone_number=phone_number,
        location_text=location_text,
        responsible_person=responsible_person,
        manager_id=manager.id,
        notes=notes,
        inn=inn,
        filial=filial,
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


# ==================== Медвакил (медпредставитель) ====================


async def list_doctors_for_manager(session: AsyncSession, manager: User, limit: int = 50) -> list[Doctor]:
    result = await session.execute(
        select(Doctor).where(Doctor.manager_id == manager.id).order_by(desc(Doctor.created_at)).limit(limit)
    )
    return list(result.scalars())


async def list_doctors_with_bonus(session: AsyncSession, manager: User) -> list[Doctor]:
    result = await session.execute(
        select(Doctor)
        .where(Doctor.manager_id == manager.id, Doctor.bonus_balance > 0)
        .order_by(desc(Doctor.bonus_balance))
    )
    return list(result.scalars())


async def list_pharmacies_for_manager(session: AsyncSession, manager: User, limit: int = 50) -> list[Pharmacy]:
    result = await session.execute(
        select(Pharmacy).where(Pharmacy.manager_id == manager.id).order_by(desc(Pharmacy.created_at)).limit(limit)
    )
    return list(result.scalars())


async def search_pharmacies(session: AsyncSession, query: str, limit: int = 10) -> list[Pharmacy]:
    like = f"%{query.strip()}%"
    result = await session.execute(
        select(Pharmacy).where(or_(Pharmacy.name.ilike(like), Pharmacy.inn.ilike(like))).limit(limit)
    )
    return list(result.scalars())


async def get_doctor(session: AsyncSession, doctor_id: int) -> Doctor | None:
    return (await session.execute(select(Doctor).where(Doctor.id == doctor_id))).scalar_one_or_none()


async def get_pharmacy(session: AsyncSession, pharmacy_id: int) -> Pharmacy | None:
    return (await session.execute(select(Pharmacy).where(Pharmacy.id == pharmacy_id))).scalar_one_or_none()


async def list_active_drugs(session: AsyncSession) -> list[Drug]:
    result = await session.execute(select(Drug).where(Drug.is_active.is_(True)).order_by(Drug.name))
    return list(result.scalars())


async def get_drug(session: AsyncSession, drug_id: int) -> Drug | None:
    return (await session.execute(select(Drug).where(Drug.id == drug_id))).scalar_one_or_none()


async def create_sale(
    session: AsyncSession,
    *,
    rep: User,
    pharmacy: Pharmacy | None,
    doctor: Doctor | None,
    items: list[tuple[Drug, int]],
) -> Sale:
    sale = Sale(
        rep_id=rep.id,
        pharmacy_id=pharmacy.id if pharmacy else None,
        doctor_id=doctor.id if doctor else None,
    )
    session.add(sale)
    await session.flush()

    total_bonus = Decimal("0")
    for drug, qty in items:
        bonus = (drug.doctor_bonus_per_pack or Decimal("0")) * qty
        total_bonus += bonus
        session.add(
            SaleItem(sale_id=sale.id, drug_id=drug.id, drug_name=drug.name, quantity=qty, bonus=bonus)
        )
        drug.stock = max(0, drug.stock - qty)

    sale.total_bonus = total_bonus
    if doctor is not None:
        doctor.bonus_balance = (doctor.bonus_balance or Decimal("0")) + total_bonus

    await log_action(session, rep, "sale_created", "sale", str(sale.id), f"bonus={total_bonus}")
    return sale


async def list_contracts_for_pharmacy(session: AsyncSession, pharmacy_id: int) -> list[Contract]:
    result = await session.execute(
        select(Contract)
        .where(Contract.pharmacy_id == pharmacy_id, Contract.status == ContractStatus.ACTIVE)
        .order_by(desc(Contract.created_at))
    )
    return list(result.scalars())


async def get_contract(session: AsyncSession, contract_id: int) -> Contract | None:
    return (await session.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()


async def request_contract(session: AsyncSession, *, pharmacy: Pharmacy, rep: User) -> Contract:
    contract = Contract(
        pharmacy_id=pharmacy.id,
        number="—",
        status=ContractStatus.REQUESTED,
        requested_by_id=rep.id,
    )
    session.add(contract)
    await session.flush()
    await log_action(session, rep, "contract_requested", "contract", str(contract.id), pharmacy.name)
    return contract


async def create_warehouse_request(
    session: AsyncSession,
    *,
    rep: User,
    pharmacy: Pharmacy | None,
    contract: Contract | None,
    items: list[tuple[Drug, int]],
) -> WarehouseRequest:
    request = WarehouseRequest(
        rep_id=rep.id,
        pharmacy_id=pharmacy.id if pharmacy else None,
        contract_id=contract.id if contract else None,
    )
    session.add(request)
    await session.flush()
    for drug, qty in items:
        session.add(
            WarehouseRequestItem(request_id=request.id, drug_id=drug.id, drug_name=drug.name, quantity=qty)
        )
    await log_action(session, rep, "warehouse_request_created", "warehouse_request", str(request.id), None)
    return request


def _wh_options():
    return (
        selectinload(WarehouseRequest.items),
        selectinload(WarehouseRequest.pharmacy),
        selectinload(WarehouseRequest.contract),
        selectinload(WarehouseRequest.rep),
    )


async def list_pending_warehouse_requests(session: AsyncSession, limit: int = 20) -> list[WarehouseRequest]:
    result = await session.execute(
        select(WarehouseRequest)
        .where(WarehouseRequest.status == WarehouseStatus.NEW)
        .order_by(WarehouseRequest.created_at)
        .options(*_wh_options())
        .limit(limit)
    )
    return list(result.scalars())


async def get_warehouse_request(session: AsyncSession, request_id: int) -> WarehouseRequest | None:
    result = await session.execute(
        select(WarehouseRequest).where(WarehouseRequest.id == request_id).options(*_wh_options())
    )
    return result.scalar_one_or_none()


async def set_warehouse_status(
    session: AsyncSession, *, request: WarehouseRequest, status: WarehouseStatus, operator: User
) -> None:
    request.status = status
    # Tasdiqlanganda склад қолдиғи тўлдирилади (буюртма бажарилди).
    if status == WarehouseStatus.APPROVED:
        for item in request.items:
            drug = await get_drug(session, item.drug_id)
            if drug is not None:
                drug.stock = drug.stock + item.quantity
    await log_action(session, operator, "warehouse_status_changed", "warehouse_request", str(request.id), status.value)


async def pay_doctor_bonus(session: AsyncSession, *, rep: User, doctor: Doctor, amount: Decimal) -> None:
    rep.balance = (rep.balance or Decimal("0")) - amount
    doctor.bonus_balance = (doctor.bonus_balance or Decimal("0")) - amount
    session.add(RepPayment(rep_id=rep.id, doctor_id=doctor.id, kind=RepPaymentKind.PAYOUT, amount=amount))
    await log_action(session, rep, "bonus_payout", "doctor", str(doctor.id), str(amount))


async def return_to_admin(session: AsyncSession, *, rep: User, amount: Decimal) -> None:
    rep.balance = (rep.balance or Decimal("0")) - amount
    session.add(RepPayment(rep_id=rep.id, doctor_id=None, kind=RepPaymentKind.RETURN, amount=amount))
    await log_action(session, rep, "podotchet_return", "user", str(rep.id), str(amount))


async def issue_podotchet(session: AsyncSession, *, rep: User, amount: Decimal) -> None:
    rep.balance = (rep.balance or Decimal("0")) + amount
    session.add(RepPayment(rep_id=rep.id, doctor_id=None, kind=RepPaymentKind.ISSUE, amount=amount))


async def create_visit(
    session: AsyncSession, *, rep: User, latitude, longitude, note: str | None
) -> VisitDiary:
    visit = VisitDiary(rep_id=rep.id, latitude=latitude, longitude=longitude, note=note)
    session.add(visit)
    await session.flush()
    await log_action(session, rep, "visit_created", "visit", str(visit.id), None)
    return visit


async def list_visits(session: AsyncSession, rep: User, limit: int = 5) -> list[VisitDiary]:
    result = await session.execute(
        select(VisitDiary).where(VisitDiary.rep_id == rep.id).order_by(desc(VisitDiary.created_at)).limit(limit)
    )
    return list(result.scalars())


async def search_visits(session: AsyncSession, rep: User, query: str, limit: int = 10) -> list[VisitDiary]:
    like = f"%{query.strip()}%"
    result = await session.execute(
        select(VisitDiary)
        .where(VisitDiary.rep_id == rep.id, VisitDiary.note.ilike(like))
        .order_by(desc(VisitDiary.created_at))
        .limit(limit)
    )
    return list(result.scalars())


async def sum_sales_qty(session: AsyncSession, *, rep_id: int, drug_id: int, start, end) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(SaleItem.quantity), 0))
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.rep_id == rep_id, SaleItem.drug_id == drug_id, SaleItem.created_at >= start, SaleItem.created_at <= end)
    )
    return int(result.scalar_one() or 0)


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

