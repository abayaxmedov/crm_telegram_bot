from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import case, desc, func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ApprovalStatus,
    AuditLog,
    BallTransaction,
    BallTxKind,
    BallTxStatus,
    Contract,
    ContractStatus,
    DailyReport,
    Doctor,
    Drug,
    DrugMaterial,
    FinanceOperation,
    FinanceType,
    Pharmacy,
    Region,
    RepPayment,
    RepPaymentKind,
    Request,
    RequestStatus,
    Role,
    Salary,
    Sale,
    SaleItem,
    ScheduledDeletion,
    User,
    VisitDiary,
    WarehouseRequest,
    WarehouseRequestItem,
    WarehouseStatus,
)


def period_window(kind: str) -> tuple[datetime | None, datetime]:
    """Hisobot davri: '10d' (10 kun), '30d' (1 oy), 'all' (to'liq). Aware UTC."""
    now = datetime.now(timezone.utc)
    if kind == "10d":
        return now - timedelta(days=10), now
    if kind == "30d":
        return now - timedelta(days=30), now
    return None, now


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
    region_id: int | None = None,
) -> User:
    user = User(
        full_name=full_name,
        role=role,
        phone_number=phone_number,
        region_id=region_id,
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


# ==================== Regionlar (owner boshqaradi) ====================


async def add_region(session: AsyncSession, *, name: str, actor: User) -> Region:
    region = Region(name=name)
    session.add(region)
    await session.flush()
    await log_action(session, actor, "region_created", "region", str(region.id), name)
    return region


async def list_regions(session: AsyncSession, *, only_active: bool = True) -> list[Region]:
    query = select(Region).order_by(Region.name)
    if only_active:
        query = query.where(Region.is_active.is_(True))
    result = await session.execute(query)
    return list(result.scalars())


async def get_region(session: AsyncSession, region_id: int) -> Region | None:
    return (await session.execute(select(Region).where(Region.id == region_id))).scalar_one_or_none()


async def add_doctor(
    session: AsyncSession,
    *,
    full_name: str,
    phone_number: str | None,
    location_text: str | None,
    class_category: str | None,
    manager: User,
    notes: str | None,
    region_id: int | None = None,
    approval_status: ApprovalStatus = ApprovalStatus.PENDING,
) -> Doctor:
    doctor = Doctor(
        full_name=full_name,
        phone_number=phone_number,
        location_text=location_text,
        class_category=class_category,
        manager_id=manager.id,
        notes=notes,
        region_id=region_id,
        approval_status=approval_status,
        created_by_id=manager.id,
    )
    session.add(doctor)
    await session.flush()
    await log_action(
        session, manager, "doctor_created", "doctor", str(doctor.id), f"{full_name} [{approval_status.value}]"
    )
    return doctor


async def list_doctors(session: AsyncSession, limit: int = 20) -> list[Doctor]:
    result = await session.execute(
        select(Doctor)
        .where(Doctor.approval_status == ApprovalStatus.APPROVED)
        .order_by(desc(Doctor.created_at))
        .limit(limit)
    )
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
    region_id: int | None = None,
    approval_status: ApprovalStatus = ApprovalStatus.PENDING,
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
        region_id=region_id,
        approval_status=approval_status,
    )
    session.add(pharmacy)
    await session.flush()
    await log_action(
        session, manager, "pharmacy_created", "pharmacy", str(pharmacy.id), f"{name} [{approval_status.value}]"
    )
    return pharmacy


async def list_pharmacies(session: AsyncSession, limit: int = 20) -> list[Pharmacy]:
    result = await session.execute(
        select(Pharmacy)
        .where(Pharmacy.approval_status == ApprovalStatus.APPROVED)
        .order_by(desc(Pharmacy.created_at))
        .limit(limit)
    )
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
    ids = await visible_rep_ids(session, actor)
    if ids is not None:
        if not ids:
            return []
        query = query.where(DailyReport.author_id.in_(ids))

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


async def list_finance_operations(
    session: AsyncSession,
    limit: int = 100,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[FinanceOperation]:
    query = select(FinanceOperation).order_by(desc(FinanceOperation.created_at)).limit(limit)
    if start is not None:
        query = query.where(FinanceOperation.created_at >= start)
    if end is not None:
        query = query.where(FinanceOperation.created_at <= end)
    result = await session.execute(query)
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
        select(Doctor)
        .where(Doctor.manager_id == manager.id, Doctor.approval_status == ApprovalStatus.APPROVED)
        .order_by(desc(Doctor.created_at))
        .limit(limit)
    )
    return list(result.scalars())


async def list_doctors_with_bonus(session: AsyncSession, manager: User) -> list[Doctor]:
    result = await session.execute(
        select(Doctor)
        .where(
            Doctor.manager_id == manager.id,
            Doctor.approval_status == ApprovalStatus.APPROVED,
            Doctor.bonus_balance > 0,
        )
        .order_by(desc(Doctor.bonus_balance))
    )
    return list(result.scalars())


async def list_doctors_visible(session: AsyncSession, actor: User, limit: int = 200) -> list[Doctor]:
    """Rolga qarab ko'rinadigan (APPROVED) doktorlar.

    owner/top/product => hammasi; regional/medvakil => o'z regioni."""
    query = (
        select(Doctor)
        .options(selectinload(Doctor.region), selectinload(Doctor.manager))
        .where(Doctor.approval_status == ApprovalStatus.APPROVED)
        .order_by(desc(Doctor.created_at))
        .limit(limit)
    )
    if actor.role in {Role.REGIONAL_MANAGER, Role.MANAGER}:
        query = query.where(Doctor.region_id == actor.region_id)
    elif actor.role not in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return []
    return list((await session.execute(query)).scalars())


async def list_pharmacies_visible(session: AsyncSession, actor: User, limit: int = 200) -> list[Pharmacy]:
    """Rolga qarab ko'rinadigan (APPROVED) dorixonalar.

    owner/top/product/operator => hammasi; regional/medvakil => o'z regioni."""
    query = (
        select(Pharmacy)
        .options(selectinload(Pharmacy.region), selectinload(Pharmacy.manager))
        .where(Pharmacy.approval_status == ApprovalStatus.APPROVED)
        .order_by(desc(Pharmacy.created_at))
        .limit(limit)
    )
    if actor.role in {Role.REGIONAL_MANAGER, Role.MANAGER}:
        query = query.where(Pharmacy.region_id == actor.region_id)
    elif actor.role not in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.OPERATOR}:
        return []
    return list((await session.execute(query)).scalars())


async def list_pharmacies_for_manager(session: AsyncSession, manager: User, limit: int = 50) -> list[Pharmacy]:
    result = await session.execute(
        select(Pharmacy)
        .where(Pharmacy.manager_id == manager.id, Pharmacy.approval_status == ApprovalStatus.APPROVED)
        .order_by(desc(Pharmacy.created_at))
        .limit(limit)
    )
    return list(result.scalars())


async def search_pharmacies(session: AsyncSession, query: str, limit: int = 10) -> list[Pharmacy]:
    like = f"%{query.strip()}%"
    result = await session.execute(
        select(Pharmacy)
        .where(
            Pharmacy.approval_status == ApprovalStatus.APPROVED,
            or_(Pharmacy.name.ilike(like), Pharmacy.inn.ilike(like)),
        )
        .limit(limit)
    )
    return list(result.scalars())


async def search_pharmacies_visible(
    session: AsyncSession, actor: User, query: str, limit: int = 20
) -> list[Pharmacy]:
    """INN (yoki nom) bo'yicha qidiruv — ko'rish ko'lami (region) bilan cheklangan.

    regional/medvakil => faqat o'z regioni; owner/top/product/operator => hammasi."""
    like = f"%{query.strip()}%"
    q = (
        select(Pharmacy)
        .options(selectinload(Pharmacy.region), selectinload(Pharmacy.manager))
        .where(
            Pharmacy.approval_status == ApprovalStatus.APPROVED,
            or_(Pharmacy.inn.ilike(like), Pharmacy.name.ilike(like)),
        )
        .order_by(desc(Pharmacy.created_at))
        .limit(limit)
    )
    if actor.role in {Role.REGIONAL_MANAGER, Role.MANAGER}:
        q = q.where(Pharmacy.region_id == actor.region_id)
    elif actor.role not in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.OPERATOR}:
        return []
    return list((await session.execute(q)).scalars())


async def get_doctor(session: AsyncSession, doctor_id: int) -> Doctor | None:
    return (await session.execute(select(Doctor).where(Doctor.id == doctor_id))).scalar_one_or_none()


async def get_doctor_with_user(session: AsyncSession, doctor_id: int) -> Doctor | None:
    """Doktor + bog'langan bot foydalanuvchisi (xabar yuborish uchun)."""
    result = await session.execute(
        select(Doctor).options(selectinload(Doctor.bot_user)).where(Doctor.id == doctor_id)
    )
    return result.scalar_one_or_none()


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
    """Sotuvni qayd etadi: narx/ball snapshot, stock kamayadi, doktordan BALL ayiriladi.

    Doktor balansi 0 bo'lsa manfiyga o'tadi (keyin kompaniya zanjir orqali to'ldiradi).
    Eski pul-bonus endi yozilmaydi (ball tizimi bilan almashtirilgan)."""
    sale = Sale(
        rep_id=rep.id,
        pharmacy_id=pharmacy.id if pharmacy else None,
        doctor_id=doctor.id if doctor else None,
    )
    session.add(sale)
    await session.flush()

    total_price = Decimal("0")
    total_ball = 0
    for drug, qty in items:
        price = drug.price or Decimal("0")
        ball = int(drug.ball or 0)
        total_price += price * qty
        total_ball += ball * qty
        session.add(
            SaleItem(
                sale_id=sale.id,
                drug_id=drug.id,
                drug_name=drug.name,
                quantity=qty,
                price=price,
                ball=ball,
            )
        )
        # Atomik kamaytirish (parallel sotuvlarda lost-update bo'lmasligi uchun).
        await session.execute(
            sa_update(Drug)
            .where(Drug.id == drug.id)
            .values(stock=case((Drug.stock >= qty, Drug.stock - qty), else_=0))
        )

    sale.total_price = total_price
    sale.total_ball = total_ball

    if doctor is not None and total_ball > 0:
        # Atomik ayirish — manfiyga o'tishi mumkin (dizayn bo'yicha).
        await session.execute(
            sa_update(Doctor)
            .where(Doctor.id == doctor.id)
            .values(ball_balance=Doctor.ball_balance - total_ball)
        )
        session.add(
            BallTransaction(
                kind=BallTxKind.SALE_DEDUCT,
                status=BallTxStatus.ACCEPTED,
                amount=total_ball,
                to_doctor_id=doctor.id,
                sale_id=sale.id,
                decided_at=datetime.now(timezone.utc),
            )
        )

    await log_action(
        session, rep, "sale_created", "sale", str(sale.id), f"price={total_price} ball={total_ball}"
    )
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


# ==================== Doktor/dorixona tasdig'i (operator) ====================


async def list_pending_doctors(session: AsyncSession, limit: int = 30) -> list[Doctor]:
    result = await session.execute(
        select(Doctor)
        .options(selectinload(Doctor.manager), selectinload(Doctor.region))
        .where(Doctor.approval_status == ApprovalStatus.PENDING)
        .order_by(Doctor.created_at)
        .limit(limit)
    )
    return list(result.scalars())


async def list_pending_pharmacies(session: AsyncSession, limit: int = 30) -> list[Pharmacy]:
    result = await session.execute(
        select(Pharmacy)
        .options(selectinload(Pharmacy.manager), selectinload(Pharmacy.region))
        .where(Pharmacy.approval_status == ApprovalStatus.PENDING)
        .order_by(Pharmacy.created_at)
        .limit(limit)
    )
    return list(result.scalars())


async def set_doctor_status(
    session: AsyncSession, *, doctor: Doctor, status: ApprovalStatus, operator: User
) -> None:
    doctor.approval_status = status
    await log_action(session, operator, "doctor_status_changed", "doctor", str(doctor.id), status.value)
    if status == ApprovalStatus.APPROVED:
        # Botga kirgan DOCTOR foydalanuvchisi bo'lsa — telefon orqali bog'laymiz.
        await try_link_user_for_doctor(session, doctor)


async def set_pharmacy_status(
    session: AsyncSession, *, pharmacy: Pharmacy, status: ApprovalStatus, operator: User
) -> None:
    pharmacy.approval_status = status
    await log_action(session, operator, "pharmacy_status_changed", "pharmacy", str(pharmacy.id), status.value)


# ==================== Ierarxik ko'rish (region bo'yicha) ====================


async def visible_rep_ids(session: AsyncSession, actor: User) -> set[int] | None:
    """actor ko'ra oladigan sotuvchi (rep) user id'lari to'plami.

    `None` => cheklovsiz (owner/TOP/product menejer hammani ko'radi).
    regional_manager => o'zi + o'z regionidagi medvakillar. manager => faqat o'zi."""
    if actor.role in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return None
    if actor.role == Role.REGIONAL_MANAGER:
        result = await session.execute(
            select(User.id).where(User.role == Role.MANAGER, User.region_id == actor.region_id)
        )
        # Regional menejer o'zi ham sotuv kirita oladi — o'zini ham ko'radi.
        return set(result.scalars()) | {actor.id}
    if actor.role == Role.MANAGER:
        return {actor.id}
    return set()


async def reps_in_scope(session: AsyncSession, actor: User) -> list[User]:
    """KPI hisob-kitobi uchun ko'rinadigan sotuvchilar (medvakil + regional) ro'yxati."""
    query = (
        select(User)
        .where(User.role.in_([Role.MANAGER, Role.REGIONAL_MANAGER]))
        .order_by(User.full_name)
    )
    ids = await visible_rep_ids(session, actor)
    if ids is not None:
        if not ids:
            return []
        query = query.where(User.id.in_(ids))
    return list((await session.execute(query)).scalars())


async def report_daily(
    session: AsyncSession,
    actor: User,
    limit: int = 200,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[DailyReport]:
    ids = await visible_rep_ids(session, actor)
    query = (
        select(DailyReport)
        .options(selectinload(DailyReport.author))
        .order_by(desc(DailyReport.created_at))
        .limit(limit)
    )
    if start is not None:
        query = query.where(DailyReport.created_at >= start)
    if end is not None:
        query = query.where(DailyReport.created_at <= end)
    if ids is not None:
        if not ids:
            return []
        query = query.where(DailyReport.author_id.in_(ids))
    return list((await session.execute(query)).scalars())


async def report_sales(
    session: AsyncSession,
    actor: User,
    limit: int = 200,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Sale]:
    ids = await visible_rep_ids(session, actor)
    query = (
        select(Sale)
        .options(
            selectinload(Sale.rep),
            selectinload(Sale.doctor),
            selectinload(Sale.pharmacy),
            selectinload(Sale.items),
        )
        .order_by(desc(Sale.created_at))
        .limit(limit)
    )
    if start is not None:
        query = query.where(Sale.created_at >= start)
    if end is not None:
        query = query.where(Sale.created_at <= end)
    if ids is not None:
        if not ids:
            return []
        query = query.where(Sale.rep_id.in_(ids))
    return list((await session.execute(query)).scalars())


async def report_visits(
    session: AsyncSession,
    actor: User,
    limit: int = 200,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[VisitDiary]:
    ids = await visible_rep_ids(session, actor)
    query = (
        select(VisitDiary).options(selectinload(VisitDiary.rep)).order_by(desc(VisitDiary.created_at)).limit(limit)
    )
    if start is not None:
        query = query.where(VisitDiary.created_at >= start)
    if end is not None:
        query = query.where(VisitDiary.created_at <= end)
    if ids is not None:
        if not ids:
            return []
        query = query.where(VisitDiary.rep_id.in_(ids))
    return list((await session.execute(query)).scalars())


# ==================== Dorilar (tovarlar) — owner CRUD ====================


async def add_drug(session: AsyncSession, *, name: str, price: Decimal, ball: int, actor: User) -> Drug:
    drug = Drug(name=name, price=price, ball=ball)
    session.add(drug)
    await session.flush()
    await log_action(session, actor, "drug_created", "drug", str(drug.id), f"{name} price={price} ball={ball}")
    return drug


async def update_drug(session: AsyncSession, *, drug: Drug, price: Decimal, ball: int, actor: User) -> Drug:
    drug.price = price
    drug.ball = ball
    await log_action(session, actor, "drug_updated", "drug", str(drug.id), f"price={price} ball={ball}")
    return drug


async def list_all_drugs(session: AsyncSession) -> list[Drug]:
    result = await session.execute(select(Drug).order_by(Drug.name))
    return list(result.scalars())


# ==================== Doktor <-> bot foydalanuvchisi bog'lash ====================


def phone_key(phone: str | None) -> str | None:
    """Telefonni solishtirish kaliti: faqat raqamlar, oxirgi 9 tasi."""
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-9:] if len(digits) >= 9 else (digits or None)


async def try_link_doctor_user(session: AsyncSession, user: User) -> Doctor | None:
    """DOCTOR-rolli foydalanuvchini telefon bo'yicha doktor yozuviga bog'laydi."""
    if user.role != Role.DOCTOR:
        return None
    key = phone_key(user.phone_number)
    if key is None:
        return None
    result = await session.execute(
        select(Doctor).where(Doctor.user_id.is_(None), Doctor.phone_number.is_not(None))
    )
    for doctor in result.scalars():
        if phone_key(doctor.phone_number) == key:
            doctor.user_id = user.id
            await log_action(session, user, "doctor_linked", "doctor", str(doctor.id), f"user={user.id}")
            return doctor
    return None


async def try_link_user_for_doctor(session: AsyncSession, doctor: Doctor) -> User | None:
    """Doktor yozuvi uchun mos DOCTOR-rolli foydalanuvchini topib bog'laydi."""
    if doctor.user_id is not None:
        return None
    key = phone_key(doctor.phone_number)
    if key is None:
        return None
    result = await session.execute(
        select(User).where(User.role == Role.DOCTOR, User.is_active.is_(True), User.phone_number.is_not(None))
    )
    for user in result.scalars():
        if phone_key(user.phone_number) == key:
            doctor.user_id = user.id
            await log_action(session, user, "doctor_linked", "doctor", str(doctor.id), f"user={user.id}")
            return user
    return None


# ==================== Ball (aksiya ballari) ====================


async def pending_outgoing_ball(session: AsyncSession, user: User) -> int:
    """Foydalanuvchining tasdiq kutayotgan chiquvchi TRANSFER ballari yig'indisi."""
    result = await session.execute(
        select(func.coalesce(func.sum(BallTransaction.amount), 0)).where(
            BallTransaction.from_user_id == user.id,
            BallTransaction.kind == BallTxKind.TRANSFER,
            BallTransaction.status == BallTxStatus.PENDING,
        )
    )
    return int(result.scalar_one() or 0)


async def available_ball(session: AsyncSession, user: User) -> int:
    """Yuborish uchun mavjud ball = balans - pending chiquvchi o'tkazmalar."""
    return int(user.ball_balance or 0) - await pending_outgoing_ball(session, user)


async def create_ball_transfer(
    session: AsyncSession,
    *,
    sender: User,
    amount: int,
    to_user: User | None = None,
    to_doctor: Doctor | None = None,
) -> BallTransaction:
    """PENDING ball o'tkazmasi. Owner uchun MINT (emissiya — balansdan ayirilmaydi)."""
    kind = BallTxKind.MINT if sender.role == Role.OWNER else BallTxKind.TRANSFER
    tx = BallTransaction(
        kind=kind,
        status=BallTxStatus.PENDING,
        amount=amount,
        from_user_id=sender.id,
        to_user_id=to_user.id if to_user else None,
        to_doctor_id=to_doctor.id if to_doctor else None,
    )
    session.add(tx)
    await session.flush()
    await log_action(session, sender, "ball_transfer_created", "ball_tx", str(tx.id), f"{kind.value} {amount}")
    return tx


async def get_ball_transaction(session: AsyncSession, tx_id: int) -> BallTransaction | None:
    result = await session.execute(
        select(BallTransaction)
        .options(
            selectinload(BallTransaction.from_user),
            selectinload(BallTransaction.to_user),
            selectinload(BallTransaction.to_doctor),
        )
        .where(BallTransaction.id == tx_id)
    )
    return result.scalar_one_or_none()


async def _claim_ball_transfer(session: AsyncSession, tx_id: int, new_status: BallTxStatus) -> bool:
    """PENDING -> new_status atomik o'tish. Parallel accept/reject/expire poygasida
    faqat bitta tomon yutadi (rowcount=1), qolganlari False oladi."""
    result = await session.execute(
        sa_update(BallTransaction)
        .where(BallTransaction.id == tx_id, BallTransaction.status == BallTxStatus.PENDING)
        .values(status=new_status, decided_at=datetime.now(timezone.utc))
    )
    return result.rowcount == 1


async def accept_ball_transfer(session: AsyncSession, tx: BallTransaction, actor: User) -> str:
    """Qabul qiluvchi tasdiqlaganda balans ATOMIK ko'chiriladi.

    Natija: 'accepted' | 'insufficient' (sender balansi yetmadi -> REJECTED)
    | 'conflict' (allaqachon qabul/rad/expire qilingan yoki tx buzilgan).

    Barcha balans o'zgarishlari SQL darajasida atomik (read-modify-write emas),
    shuning uchun parallel tasdiqlashlarda lost-update bo'lmaydi."""
    if not await _claim_ball_transfer(session, tx.id, BallTxStatus.ACCEPTED):
        return "conflict"

    if tx.kind == BallTxKind.TRANSFER:
        # Shartli atomik ayirish: balans yetgandagina o'tadi.
        deducted = await session.execute(
            sa_update(User)
            .where(User.id == tx.from_user_id, User.ball_balance >= tx.amount)
            .values(ball_balance=User.ball_balance - tx.amount)
        )
        if deducted.rowcount != 1:
            await session.execute(
                sa_update(BallTransaction)
                .where(BallTransaction.id == tx.id)
                .values(status=BallTxStatus.REJECTED)
            )
            await log_action(session, actor, "ball_transfer_autoreject", "ball_tx", str(tx.id), "insufficient")
            return "insufficient"

    if tx.to_user_id is not None:
        await session.execute(
            sa_update(User).where(User.id == tx.to_user_id).values(ball_balance=User.ball_balance + tx.amount)
        )
    elif tx.to_doctor_id is not None:
        await session.execute(
            sa_update(Doctor)
            .where(Doctor.id == tx.to_doctor_id)
            .values(ball_balance=Doctor.ball_balance + tx.amount)
        )
    else:
        await session.execute(
            sa_update(BallTransaction).where(BallTransaction.id == tx.id).values(status=BallTxStatus.REJECTED)
        )
        return "conflict"

    await log_action(session, actor, "ball_transfer_accepted", "ball_tx", str(tx.id), str(tx.amount))
    return "accepted"


async def finish_ball_transfer(
    session: AsyncSession, tx: BallTransaction, actor: User | None, status: BallTxStatus
) -> bool:
    """REJECTED / EXPIRED holatiga atomik o'tkazish (balans o'zgarmaydi).

    False => tx allaqachon boshqa holatga o'tgan (masalan parallel accept yutgan)."""
    if not await _claim_ball_transfer(session, tx.id, status):
        return False
    await log_action(session, actor, f"ball_transfer_{status.value}", "ball_tx", str(tx.id), str(tx.amount))
    return True


async def get_ball_balance(
    session: AsyncSession, *, user_id: int | None = None, doctor_id: int | None = None
) -> int:
    """Joriy ball balansi (atomik UPDATE'lardan keyin ORM obyekt eskirgani uchun)."""
    if user_id is not None:
        value = await session.scalar(select(User.ball_balance).where(User.id == user_id))
    elif doctor_id is not None:
        value = await session.scalar(select(Doctor.ball_balance).where(Doctor.id == doctor_id))
    else:
        value = 0
    return int(value or 0)


async def doctors_for_ball_transfer(session: AsyncSession, rep: User) -> list[Doctor]:
    """Medvakil ball yubora oladigan doktorlar: o'z regioni, APPROVED, botga ulangan."""
    result = await session.execute(
        select(Doctor)
        .options(selectinload(Doctor.bot_user))
        .where(
            Doctor.approval_status == ApprovalStatus.APPROVED,
            Doctor.region_id == rep.region_id,
            Doctor.user_id.is_not(None),
        )
        .order_by(Doctor.full_name)
    )
    doctors = list(result.scalars())
    return [d for d in doctors if d.bot_user is not None and d.bot_user.telegram_id is not None]


async def ball_scope(session: AsyncSession, actor: User) -> tuple[set[int] | None, set[int] | None]:
    """Ball hisoboti ko'lami: (user_id'lar, doktor_id'lar). (None, None) => cheklovsiz.

    owner/top/product => hammasi; regional => o'zi + region medvakillari + region doktorlari;
    medvakil => o'zi + region doktorlari."""
    if actor.role in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return None, None

    doctor_ids = set(
        (
            await session.execute(
                select(Doctor.id).where(
                    Doctor.region_id == actor.region_id,
                    Doctor.approval_status == ApprovalStatus.APPROVED,
                )
            )
        ).scalars()
    )
    user_ids = {actor.id}
    if actor.role == Role.REGIONAL_MANAGER:
        manager_ids = set(
            (
                await session.execute(
                    select(User.id).where(User.role == Role.MANAGER, User.region_id == actor.region_id)
                )
            ).scalars()
        )
        user_ids |= manager_ids
    return user_ids, doctor_ids


async def ball_balances_overview(session: AsyncSession, actor: User) -> tuple[list[User], list[Doctor]]:
    """Ko'lamga mos joriy ball balanslari: (foydalanuvchilar, doktorlar)."""
    user_ids, doctor_ids = await ball_scope(session, actor)

    user_query = (
        select(User)
        .options(selectinload(User.region))
        .where(
            User.is_active.is_(True),
            User.role.in_([Role.OWNER, Role.TOP_MANAGER, Role.REGIONAL_MANAGER, Role.MANAGER]),
        )
        .order_by(User.role, User.full_name)
    )
    doctor_query = (
        select(Doctor)
        .options(selectinload(Doctor.region))
        .where(Doctor.approval_status == ApprovalStatus.APPROVED)
        .order_by(Doctor.full_name)
    )
    if user_ids is not None:
        users = (
            list((await session.execute(user_query.where(User.id.in_(user_ids)))).scalars()) if user_ids else []
        )
    else:
        users = list((await session.execute(user_query)).scalars())

    if doctor_ids is not None:
        doctors = (
            list((await session.execute(doctor_query.where(Doctor.id.in_(doctor_ids)))).scalars())
            if doctor_ids
            else []
        )
    else:
        doctors = list((await session.execute(doctor_query)).scalars())
    return users, doctors


async def ball_transactions_in_period(
    session: AsyncSession,
    actor: User,
    start: datetime | None,
    end: datetime,
    limit: int = 500,
) -> list[BallTransaction]:
    user_ids, doctor_ids = await ball_scope(session, actor)
    query = (
        select(BallTransaction)
        .options(
            selectinload(BallTransaction.from_user),
            selectinload(BallTransaction.to_user),
            selectinload(BallTransaction.to_doctor),
        )
        .where(BallTransaction.created_at <= end)
        .order_by(desc(BallTransaction.created_at))
        .limit(limit)
    )
    if start is not None:
        query = query.where(BallTransaction.created_at >= start)
    if user_ids is not None:
        conditions = []
        if user_ids:
            conditions.append(BallTransaction.from_user_id.in_(user_ids))
            conditions.append(BallTransaction.to_user_id.in_(user_ids))
        if doctor_ids:
            conditions.append(BallTransaction.to_doctor_id.in_(doctor_ids))
        if not conditions:
            return []
        query = query.where(or_(*conditions))
    return list((await session.execute(query)).scalars())


# ==================== Analitika (webapp + Excel) ====================


async def sales_item_rows(
    session: AsyncSession,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    region_id: int | None = None,
    rep_id: int | None = None,
) -> list[dict]:
    """Sotuv pozitsiyalari (tekis qatorlar) — analitika/Excel uchun.

    Har qator: sana, rep, region, dorixona, doktor, dori, soni, narx, ball, tushum."""
    query = (
        select(SaleItem, Sale, User, Region, Pharmacy, Doctor)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(User, User.id == Sale.rep_id)
        .outerjoin(Region, Region.id == User.region_id)
        .outerjoin(Pharmacy, Pharmacy.id == Sale.pharmacy_id)
        .outerjoin(Doctor, Doctor.id == Sale.doctor_id)
        .order_by(desc(SaleItem.created_at))
    )
    if start is not None:
        query = query.where(SaleItem.created_at >= start)
    if end is not None:
        query = query.where(SaleItem.created_at <= end)
    if region_id is not None:
        query = query.where(User.region_id == region_id)
    if rep_id is not None:
        query = query.where(Sale.rep_id == rep_id)

    rows: list[dict] = []
    for item, sale, rep, region, pharmacy, doctor in (await session.execute(query)).all():
        price = Decimal(str(item.price or 0))
        rows.append(
            {
                "created_at": item.created_at,
                "sale_id": sale.id,
                "rep_id": rep.id,
                "rep_name": rep.full_name,
                "region_id": region.id if region else None,
                "region_name": region.name if region else None,
                "pharmacy": pharmacy.name if pharmacy else None,
                "doctor": doctor.full_name if doctor else None,
                "drug_name": item.drug_name,
                "qty": int(item.quantity or 0),
                "price": price,
                "ball": int(item.ball or 0),
                "revenue": price * int(item.quantity or 0),
                "ball_total": int(item.ball or 0) * int(item.quantity or 0),
            }
        )
    return rows


async def list_sellers(session: AsyncSession) -> list[User]:
    """Sotuv kiritadigan foydalanuvchilar (webapp filtri uchun)."""
    result = await session.execute(
        select(User)
        .options(selectinload(User.region))
        .where(User.role.in_([Role.MANAGER, Role.REGIONAL_MANAGER]), User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return list(result.scalars())


# ==================== Dorixona tasdig'i (shartnoma bilan) ====================


async def approve_pharmacy_with_contract(
    session: AsyncSession,
    *,
    pharmacy: Pharmacy,
    operator: User,
    contract_number: str,
    contract_file_id: str,
    new_name: str | None = None,
) -> Contract:
    """Operator tasdig'i: nom tuzatish (ixtiyoriy) + shartnoma raqami/fayli + APPROVED."""
    if new_name:
        pharmacy.name = new_name
    pharmacy.approval_status = ApprovalStatus.APPROVED
    contract = Contract(
        pharmacy_id=pharmacy.id,
        number=contract_number,
        status=ContractStatus.ACTIVE,
        requested_by_id=operator.id,
        file_id=contract_file_id,
    )
    session.add(contract)
    await session.flush()
    await log_action(
        session, operator, "pharmacy_approved_contract", "pharmacy", str(pharmacy.id), f"contract={contract_number}"
    )
    return contract


# ==================== Rejalashtirilgan o'chirish (doktor xabarlari) ====================


async def schedule_deletion(
    session: AsyncSession,
    *,
    chat_id: int,
    message_id: int,
    delete_at: datetime,
    ball_tx_id: int | None = None,
) -> ScheduledDeletion:
    row = ScheduledDeletion(chat_id=chat_id, message_id=message_id, delete_at=delete_at, ball_tx_id=ball_tx_id)
    session.add(row)
    await session.flush()
    return row


async def due_deletions(session: AsyncSession, now: datetime, limit: int = 50) -> list[ScheduledDeletion]:
    result = await session.execute(
        select(ScheduledDeletion).where(ScheduledDeletion.delete_at <= now).order_by(ScheduledDeletion.delete_at).limit(limit)
    )
    return list(result.scalars())


# ==================== Dori materiallari (TOP menejer yuklaydi) ====================


async def add_material(
    session: AsyncSession, *, title: str, file_id: str, file_name: str | None, uploaded_by: User
) -> DrugMaterial:
    material = DrugMaterial(title=title, file_id=file_id, file_name=file_name, uploaded_by_id=uploaded_by.id)
    session.add(material)
    await session.flush()
    await log_action(session, uploaded_by, "material_uploaded", "material", str(material.id), title)
    return material


async def list_materials(session: AsyncSession, limit: int = 50) -> list[DrugMaterial]:
    result = await session.execute(
        select(DrugMaterial)
        .where(DrugMaterial.is_active.is_(True))
        .order_by(desc(DrugMaterial.created_at))
        .limit(limit)
    )
    return list(result.scalars())


async def get_material(session: AsyncSession, material_id: int) -> DrugMaterial | None:
    return (
        await session.execute(select(DrugMaterial).where(DrugMaterial.id == material_id))
    ).scalar_one_or_none()


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

