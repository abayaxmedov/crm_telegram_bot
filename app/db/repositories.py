from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import desc, func, or_, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

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
    Lpu,
    Pharmacy,
    PharmacyStock,
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
    Wholesaler,
    WholesaleIncome,
    WholesaleIncomeItem,
    WarehouseStatus,
)


def period_window(kind: str) -> tuple[datetime | None, datetime]:
    """Hisobot davri: '5d', '10d', '30d' (1 oy), 'all' (to'liq). Aware UTC."""
    now = datetime.now(timezone.utc)
    if kind == "5d":
        return now - timedelta(days=5), now
    if kind == "10d":
        return now - timedelta(days=10), now
    if kind == "30d":
        return now - timedelta(days=30), now
    return None, now


def make_invite_token() -> str:
    return secrets.token_urlsafe(24)


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.region)).where(User.telegram_id == telegram_id)
    )
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
    lpu_id: int | None = None,
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
        lpu_id=lpu_id,
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
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> Pharmacy:
    pharmacy = Pharmacy(
        name=name,
        phone_number=phone_number,
        location_text=location_text,
        latitude=latitude,
        longitude=longitude,
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
    target_name: str | None = None,
    text: str | None = None,
    voice_file_id: str | None = None,
    doctor_id: int | None = None,
    pharmacy_id: int | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> DailyReport:
    report = DailyReport(
        author_id=author.id,
        target_type=target_type,
        target_name=target_name,
        doctor_id=doctor_id,
        pharmacy_id=pharmacy_id,
        text=text,
        voice_file_id=voice_file_id,
        latitude=latitude,
        longitude=longitude,
    )
    session.add(report)
    await session.flush()
    await log_action(session, author, "daily_report_created", "daily_report", str(report.id), target_type)
    return report


async def edit_doctor(
    session: AsyncSession,
    *,
    doctor: Doctor,
    actor: User,
    full_name: str | None = None,
    phone_number: str | None = None,
    class_category: str | None = None,
    region_id: int | None = None,
    lpu_id: int | None = None,
) -> None:
    """Doktor ma'lumotlarini tahrirlash (owner/TOP/product). Faqat berilgan maydonlar."""
    changes: list[str] = []
    if full_name is not None:
        doctor.full_name = full_name
        changes.append("full_name")
    if phone_number is not None:
        doctor.phone_number = phone_number
        changes.append("phone")
    if class_category is not None:
        doctor.class_category = class_category
        changes.append("category")
    if region_id is not None:
        doctor.region_id = region_id
        changes.append(f"region={region_id}")
    if lpu_id is not None:
        doctor.lpu_id = lpu_id
        changes.append(f"lpu={lpu_id}")
    await session.flush()
    await log_action(session, actor, "doctor_edited", "doctor", str(doctor.id), ", ".join(changes) or "-")


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


async def list_doctors_visible(
    session: AsyncSession,
    actor: User,
    limit: int = 200,
    *,
    lpu_id: int | None = None,
    only_approved: bool = False,
) -> list[Doctor]:
    """Rolga qarab ko'rinadigan doktorlar.

    owner/top/product => hammasi; regional menejer => o'z REGIONI (o'zi yaratmagan
    bo'lsa ham); medvakil => FAQAT o'zi yaratgan. `lpu_id` berilsa — shu ЛПУ doktorlari.

    `only_approved=True` — faqat ✅ tasdiqlanganlar (SOTUV/BALL uchun). Standart holda
    tasdiqsizlar ham qaytadi (ro'yxat/hisobot uchun — maqom to'siq emas, belgi)."""
    query = (
        select(Doctor)
        .options(
            selectinload(Doctor.region),
            selectinload(Doctor.manager),
            selectinload(Doctor.bot_user),
            selectinload(Doctor.lpu),
        )
        .order_by(desc(Doctor.created_at))
        .limit(limit)
    )
    if only_approved:
        query = query.where(Doctor.approval_status == ApprovalStatus.APPROVED)
    if actor.role == Role.REGIONAL_MANAGER:
        query = query.where(Doctor.region_id == actor.region_id)
    elif actor.role == Role.MANAGER:
        query = query.where(Doctor.manager_id == actor.id)
    elif actor.role not in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return []
    if lpu_id is not None:
        query = query.where(Doctor.lpu_id == lpu_id)
    return list((await session.execute(query)).scalars())


async def list_pharmacies_visible(session: AsyncSession, actor: User, limit: int = 200) -> list[Pharmacy]:
    """Rolga qarab ko'rinadigan (APPROVED) dorixonalar.

    owner/top/product/operator => hammasi; regional => o'z regioni; medvakil => faqat o'zi yaratgan."""
    query = (
        select(Pharmacy)
        .options(selectinload(Pharmacy.region), selectinload(Pharmacy.manager))
        .where(Pharmacy.approval_status == ApprovalStatus.APPROVED)
        .order_by(desc(Pharmacy.created_at))
        .limit(limit)
    )
    if actor.role == Role.MANAGER:
        query = query.where(Pharmacy.manager_id == actor.id)
    elif actor.role == Role.REGIONAL_MANAGER:
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

    regional => o'z regioni; medvakil => faqat o'zi yaratgan; owner/top/product/operator => hammasi."""
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
    if actor.role == Role.MANAGER:
        q = q.where(Pharmacy.manager_id == actor.id)
    elif actor.role == Role.REGIONAL_MANAGER:
        q = q.where(Pharmacy.region_id == actor.region_id)
    elif actor.role not in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.OPERATOR}:
        return []
    return list((await session.execute(q)).scalars())


async def get_doctor(session: AsyncSession, doctor_id: int) -> Doctor | None:
    return (await session.execute(select(Doctor).where(Doctor.id == doctor_id))).scalar_one_or_none()


async def get_doctor_by_user(session: AsyncSession, user_id: int) -> Doctor | None:
    """Bot foydalanuvchisiga bog'langan doktor yozuvi (doktor o'z balansini ko'rishi uchun)."""
    return (
        await session.execute(select(Doctor).where(Doctor.user_id == user_id))
    ).scalar_one_or_none()


async def get_doctor_with_user(session: AsyncSession, doctor_id: int) -> Doctor | None:
    """Doktor + bog'langan bot foydalanuvchisi (xabar yuborish uchun)."""
    result = await session.execute(
        select(Doctor).options(selectinload(Doctor.bot_user)).where(Doctor.id == doctor_id)
    )
    return result.scalar_one_or_none()


async def get_doctor_full(session: AsyncSession, doctor_id: int) -> Doctor | None:
    """Doktor + region + masъул + ЛПУ + bot_user (detail karta uchun)."""
    result = await session.execute(
        select(Doctor)
        .options(
            selectinload(Doctor.region),
            selectinload(Doctor.manager),
            selectinload(Doctor.lpu),
            selectinload(Doctor.bot_user),
        )
        .where(Doctor.id == doctor_id)
    )
    return result.scalar_one_or_none()


# ==================== ЛПУ (Davolash-profilaktika muassasasi) ====================


async def add_lpu(
    session: AsyncSession,
    *,
    name: str,
    address: str | None,
    creator: User,
    region_id: int | None = None,
) -> "Lpu":
    lpu = Lpu(
        name=name,
        address=address,
        region_id=region_id,
        created_by_id=creator.id,
    )
    session.add(lpu)
    await session.flush()
    await log_action(session, creator, "lpu_created", "lpu", str(lpu.id), name)
    return lpu


async def list_lpus_visible(session: AsyncSession, actor: User, limit: int = 200) -> list["Lpu"]:
    """Rolga qarab ko'rinadigan ЛПУ: owner/top/product => hammasi; regional/medvakil => o'z regioni.

    Maqom (⏳/✅) bo'yicha FILTRLANMAYDI — tasdiqsiz ЛПУ ham ishlatilaveradi."""
    query = select(Lpu).options(selectinload(Lpu.region)).order_by(desc(Lpu.created_at)).limit(limit)
    if actor.role in {Role.REGIONAL_MANAGER, Role.MANAGER}:
        query = query.where(Lpu.region_id == actor.region_id)
    elif actor.role not in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return []
    return list((await session.execute(query)).scalars())


async def list_lpus_in_region(session: AsyncSession, region_id: int | None, limit: int = 200) -> list["Lpu"]:
    """Berilgan regiondagi ЛПУ ro'yxati (doktor yaratishда tanlash uchun).

    region_id=None bo'lsa BO'SH ro'yxat qaytadi — region aniq bo'lmaganда butun
    tarmoq ЛПУлари ko'rinиб ketmasligi uchun (region-scope himoyasi)."""
    if region_id is None:
        return []
    query = select(Lpu).where(Lpu.region_id == region_id).order_by(Lpu.name).limit(limit)
    return list((await session.execute(query)).scalars())


async def get_lpu(session: AsyncSession, lpu_id: int) -> "Lpu | None":
    return (await session.execute(select(Lpu).where(Lpu.id == lpu_id))).scalar_one_or_none()


async def get_lpu_full(session: AsyncSession, lpu_id: int) -> "Lpu | None":
    result = await session.execute(
        select(Lpu)
        .options(selectinload(Lpu.region), selectinload(Lpu.created_by))
        .where(Lpu.id == lpu_id)
    )
    return result.scalar_one_or_none()


async def get_pharmacy(session: AsyncSession, pharmacy_id: int) -> Pharmacy | None:
    return (await session.execute(select(Pharmacy).where(Pharmacy.id == pharmacy_id))).scalar_one_or_none()


async def get_pharmacy_full(session: AsyncSession, pharmacy_id: int) -> Pharmacy | None:
    """Dorixona + region (detail karta uchun)."""
    result = await session.execute(
        select(Pharmacy).options(selectinload(Pharmacy.region)).where(Pharmacy.id == pharmacy_id)
    )
    return result.scalar_one_or_none()


async def list_active_drugs(session: AsyncSession) -> list[Drug]:
    result = await session.execute(select(Drug).where(Drug.is_active.is_(True)).order_by(Drug.name))
    return list(result.scalars())


async def get_drug(session: AsyncSession, drug_id: int) -> Drug | None:
    return (await session.execute(select(Drug).where(Drug.id == drug_id))).scalar_one_or_none()


# ==================== Dorixona qoldig'i (PharmacyStock) — ombor CHEKSIZ, saqlanmaydi ====================


async def get_pharmacy_stock_qty(session: AsyncSession, pharmacy_id: int, drug_id: int) -> int:
    """Dorixonadagi bitta dorining qoldig'i (остаток). Yo'q bo'lsa 0."""
    val = (
        await session.execute(
            select(PharmacyStock.quantity).where(
                PharmacyStock.pharmacy_id == pharmacy_id, PharmacyStock.drug_id == drug_id
            )
        )
    ).scalar_one_or_none()
    return int(val or 0)


async def bump_pharmacy_stock(session: AsyncSession, *, pharmacy_id: int, drug_id: int, delta: int) -> None:
    """Dorixona qoldig'ини delta ga o'zgartiradi (upsert; 0 dan past bo'lmaydi)."""
    ps = (
        await session.execute(
            select(PharmacyStock).where(
                PharmacyStock.pharmacy_id == pharmacy_id, PharmacyStock.drug_id == drug_id
            )
        )
    ).scalar_one_or_none()
    if ps is None:
        ps = PharmacyStock(pharmacy_id=pharmacy_id, drug_id=drug_id, quantity=max(0, delta))
        session.add(ps)
    else:
        ps.quantity = max(0, int(ps.quantity or 0) + delta)
    await session.flush()


async def list_pharmacy_stock(session: AsyncSession, pharmacy_id: int) -> list[Drug]:
    """Dorixonada qoldig'i > 0 bo'lgan dorilar (Drug obyektiga `_pharmacy_qty` biriktiriladi)."""
    rows = (
        await session.execute(
            select(Drug, PharmacyStock.quantity)
            .join(PharmacyStock, PharmacyStock.drug_id == Drug.id)
            .where(
                PharmacyStock.pharmacy_id == pharmacy_id,
                PharmacyStock.quantity > 0,
                Drug.is_active.is_(True),
            )
            .order_by(Drug.name)
        )
    ).all()
    result: list[Drug] = []
    for drug, qty in rows:
        drug._pharmacy_qty = int(qty)
        result.append(drug)
    return result


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
        # Sotuv to'liq (100%) narxda hisoblanadi.
        price = drug.price_100 or drug.price or Decimal("0")
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
        # Sotuv tanlangan DORIXONA qoldig'ini kamaytiradi (ombor emas).
        if pharmacy is not None:
            await bump_pharmacy_stock(session, pharmacy_id=pharmacy.id, drug_id=drug.id, delta=-qty)

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


def drug_price_for(drug: Drug, payment_percent: int) -> Decimal:
    """Apteka to'lov shartiga mos narx: 100% => price_100 (arzon), 50% => price_50 (qimmat)."""
    if int(payment_percent) == 50:
        return drug.price_50 or Decimal("0")
    return drug.price_100 or Decimal("0")


async def create_warehouse_request(
    session: AsyncSession,
    *,
    rep: User,
    pharmacy: Pharmacy | None,
    contract: Contract | None,
    items: list[tuple[Drug, int]],
    payment_percent: int = 100,
) -> WarehouseRequest:
    """Zayavka: apteka boshlang'ich to'lov sharti (100/50) bo'yicha narx snapshot qilinadi."""
    request = WarehouseRequest(
        rep_id=rep.id,
        pharmacy_id=pharmacy.id if pharmacy else None,
        contract_id=contract.id if contract else None,
        payment_percent=int(payment_percent),
    )
    session.add(request)
    await session.flush()
    for drug, qty in items:
        session.add(
            WarehouseRequestItem(
                request_id=request.id,
                drug_id=drug.id,
                drug_name=drug.name,
                quantity=qty,
                price=drug_price_for(drug, payment_percent),
            )
        )
    await log_action(
        session, rep, "warehouse_request_created", "warehouse_request", str(request.id),
        f"payment={payment_percent}%",
    )
    return request


def warehouse_request_total(request: WarehouseRequest) -> Decimal:
    """Zayavka summasi (items EAGER-LOAD bo'lishi shart)."""
    return sum((it.price or Decimal("0")) * it.quantity for it in request.items) or Decimal("0")


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
    session: AsyncSession,
    *,
    request: WarehouseRequest,
    status: WarehouseStatus,
    operator: User,
    shipped: dict[int, int] | None = None,
) -> None:
    """Zayavka holatini o'zgartiradi.

    APPROVED — operator OTGRUZKA kiritgandan keyin: apteka qoldig'i so'ralgan emas,
    `shipped` (item_id -> jo'natilgan miqdor) bo'yicha o'zgaradi. Ombor CHEKSIZ —
    ombor qoldig'i saqlanmaydi, operator xohlagan miqdorni jo'nata oladi.
    REJECTED — qoldiq umuman o'zgarmaydi."""
    if status == WarehouseStatus.APPROVED:
        shipped = shipped or {}
        for item in request.items:
            qty = max(0, int(shipped.get(item.id, 0)))
            item.shipped_quantity = qty
            if qty and request.pharmacy_id is not None:
                await bump_pharmacy_stock(
                    session, pharmacy_id=request.pharmacy_id, drug_id=item.drug_id, delta=qty
                )
    request.status = status
    await log_action(session, operator, "warehouse_status_changed", "warehouse_request", str(request.id), status.value)


def warehouse_shipped_total(request: WarehouseRequest) -> Decimal:
    """Haqiqatda jo'natilgan miqdor bo'yicha summa (items EAGER-LOAD bo'lishi shart)."""
    return sum(
        ((it.price or Decimal("0")) * (it.shipped_quantity or 0) for it in request.items), Decimal("0")
    )


# ==================== Оптом (ulgurji yetkazib beruvchi) ====================


async def add_wholesaler(
    session: AsyncSession, *, name: str, inn: str | None, phone_number: str | None, actor: User
) -> Wholesaler:
    """Optom yaratish — faqat OWNER (ruxsat handler'da tekshiriladi)."""
    wholesaler = Wholesaler(name=name, inn=inn, phone_number=phone_number, created_by_id=actor.id)
    session.add(wholesaler)
    await session.flush()
    await log_action(session, actor, "wholesaler_created", "wholesaler", str(wholesaler.id), name)
    return wholesaler


async def list_wholesalers(session: AsyncSession, *, only_active: bool = True) -> list[Wholesaler]:
    query = select(Wholesaler)
    if only_active:
        query = query.where(Wholesaler.is_active.is_(True))
    return list((await session.execute(query.order_by(Wholesaler.name))).scalars())


async def get_wholesaler(session: AsyncSession, wholesaler_id: int | None) -> Wholesaler | None:
    if not wholesaler_id:
        return None
    return (
        await session.execute(select(Wholesaler).where(Wholesaler.id == wholesaler_id))
    ).scalar_one_or_none()


# ==================== Оптомдан приход ====================


async def create_wholesale_income(
    session: AsyncSession, *, rep: User, pharmacy: Pharmacy, wholesaler: Wholesaler, items: list[tuple[Drug, int]]
) -> WholesaleIncome:
    """PENDING prixod — TOP menejer tasdiqlagunча apteka qoldig'i O'ZGARMAYDI."""
    income = WholesaleIncome(rep_id=rep.id, pharmacy_id=pharmacy.id, wholesaler_id=wholesaler.id)
    session.add(income)
    await session.flush()
    for drug, qty in items:
        session.add(
            WholesaleIncomeItem(income_id=income.id, drug_id=drug.id, drug_name=drug.name, quantity=qty)
        )
    await log_action(
        session, rep, "wholesale_income_created", "wholesale_income", str(income.id), wholesaler.name
    )
    await session.flush()
    return income


def _wi_options():
    return (
        selectinload(WholesaleIncome.items),
        selectinload(WholesaleIncome.pharmacy),
        selectinload(WholesaleIncome.wholesaler),
        selectinload(WholesaleIncome.rep),
    )


async def get_wholesale_income(session: AsyncSession, income_id: int) -> WholesaleIncome | None:
    return (
        await session.execute(
            select(WholesaleIncome).where(WholesaleIncome.id == income_id).options(*_wi_options())
        )
    ).scalar_one_or_none()


async def list_pending_wholesale_incomes(session: AsyncSession, limit: int = 20) -> list[WholesaleIncome]:
    return list(
        (
            await session.execute(
                select(WholesaleIncome)
                .where(WholesaleIncome.status == ApprovalStatus.PENDING)
                .order_by(WholesaleIncome.created_at)
                .options(*_wi_options())
                .limit(limit)
            )
        ).scalars()
    )


async def set_wholesale_income_status(
    session: AsyncSession, *, income: WholesaleIncome, status: ApprovalStatus, actor: User
) -> None:
    """APPROVED — apteka qoldig'i prixod miqdoriga oshadi; REJECTED — qoldiq tegilmaydi."""
    if status == ApprovalStatus.APPROVED and income.pharmacy_id is not None:
        for item in income.items:
            await bump_pharmacy_stock(
                session, pharmacy_id=income.pharmacy_id, drug_id=item.drug_id, delta=int(item.quantity)
            )
    income.status = status
    await log_action(
        session, actor, "wholesale_income_status_changed", "wholesale_income", str(income.id), status.value
    )


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


async def list_pending_lpus(session: AsyncSession, limit: int = 30) -> list["Lpu"]:
    """TOP menejer tasdig'ini kutayotgan ЛПУлар."""
    return list(
        (
            await session.execute(
                select(Lpu)
                .options(selectinload(Lpu.region), selectinload(Lpu.created_by))
                .where(Lpu.approval_status == ApprovalStatus.PENDING)
                .order_by(Lpu.created_at)
                .limit(limit)
            )
        ).scalars()
    )


async def set_lpu_status(
    session: AsyncSession, *, lpu: "Lpu", status: ApprovalStatus, actor: User
) -> bool:
    """ЛПУ maqomini o'zgartiradi (faqat belgi — hech narsani to'smaydi).

    False => allaqachon ko'rib chiqilgan (parallel tasdiqlashda ikkinchisi yutqazadi)."""
    if lpu.approval_status != ApprovalStatus.PENDING:
        return False
    lpu.approval_status = status
    await log_action(session, actor, "lpu_status_changed", "lpu", str(lpu.id), status.value)
    return True


async def set_doctor_status(
    session: AsyncSession, *, doctor: Doctor, status: ApprovalStatus, operator: User
) -> bool:
    """Doktor maqomini o'zgartiradi (maqom — sotuv/ball uchun darvoza, yaratishga to'siq emas).

    False => allaqachon ko'rib chiqilgan (parallel tasdiqlashda ikkinchisi yutqazadi)."""
    if doctor.approval_status != ApprovalStatus.PENDING:
        return False
    doctor.approval_status = status
    await log_action(session, operator, "doctor_status_changed", "doctor", str(doctor.id), status.value)
    if status == ApprovalStatus.APPROVED:
        # Botga kirgan DOCTOR foydalanuvchisi bo'lsa — telefon orqali bog'laymiz.
        await try_link_user_for_doctor(session, doctor)
    return True


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


async def add_drug(
    session: AsyncSession, *, name: str, price_100: Decimal, price_50: Decimal, ball: int, actor: User
) -> Drug:
    """Yangi dori: 100% to'lov narxi (arzon) + 50% bo'lib to'lash narxi (qimmat) + ball."""
    drug = Drug(name=name, price_100=price_100, price_50=price_50, price=price_100, ball=ball)
    session.add(drug)
    await session.flush()
    await log_action(
        session, actor, "drug_created", "drug", str(drug.id),
        f"{name} 100%={price_100} 50%={price_50} ball={ball}",
    )
    return drug


async def update_drug(
    session: AsyncSession, *, drug: Drug, price_100: Decimal, price_50: Decimal, ball: int, actor: User
) -> Drug:
    drug.price_100 = price_100
    drug.price_50 = price_50
    drug.price = price_100  # legacy ustun — 100% narx bilan sinxron
    drug.ball = ball
    await log_action(
        session, actor, "drug_updated", "drug", str(drug.id), f"100%={price_100} 50%={price_50} ball={ball}"
    )
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


async def try_link_pharmacy_user(session: AsyncSession, user: User) -> Pharmacy | None:
    """PHARMACY-rolli foydalanuvchini telefon bo'yicha dorixona yozuviga bog'laydi.

    Doktor bilan aynan bir xil naqsh: solishtiruv `phone_key` (oxirgi 9 raqam)."""
    if user.role != Role.PHARMACY:
        return None
    key = phone_key(user.phone_number)
    if key is None:
        return None
    result = await session.execute(
        select(Pharmacy).where(Pharmacy.user_id.is_(None), Pharmacy.phone_number.is_not(None))
    )
    for pharmacy in result.scalars():
        if phone_key(pharmacy.phone_number) == key:
            pharmacy.user_id = user.id
            await log_action(session, user, "pharmacy_linked", "pharmacy", str(pharmacy.id), f"user={user.id}")
            return pharmacy
    return None


async def get_pharmacy_by_user(session: AsyncSession, user_id: int) -> Pharmacy | None:
    return (
        await session.execute(select(Pharmacy).where(Pharmacy.user_id == user_id))
    ).scalar_one_or_none()


async def get_pharmacy_with_user(session: AsyncSession, pharmacy_id: int | None) -> Pharmacy | None:
    if not pharmacy_id:
        return None
    return (
        await session.execute(
            select(Pharmacy).options(selectinload(Pharmacy.bot_user)).where(Pharmacy.id == pharmacy_id)
        )
    ).scalar_one_or_none()


async def pharmacies_for_ball_transfer(session: AsyncSession, rep: User) -> list[Pharmacy]:
    """Ball yubora oladigan dorixonalar: ko'rinish qoidasi bo'yicha, APPROVED, botga ulangan."""
    scope = (
        Pharmacy.region_id == rep.region_id
        if rep.role == Role.REGIONAL_MANAGER
        else Pharmacy.manager_id == rep.id
    )
    result = await session.execute(
        select(Pharmacy)
        .options(selectinload(Pharmacy.bot_user))
        .where(
            Pharmacy.approval_status == ApprovalStatus.APPROVED,
            scope,
            Pharmacy.user_id.is_not(None),
        )
        .order_by(Pharmacy.name)
    )
    return [p for p in result.scalars() if p.bot_user is not None and p.bot_user.telegram_id is not None]


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
    """Tasdiq kutayotgan chiquvchi ballar (TRANSFER + GIFT) yig'indisi.

    Ikkalasi ham qabul/tasdiq paytida balansdan ayiriladi — shuning uchun ikkalasi
    ham `available_ball` da band hisoblanadi (aks holda bir ballni ikki marta
    yuborib bo'lardi)."""
    result = await session.execute(
        select(func.coalesce(func.sum(BallTransaction.amount), 0)).where(
            BallTransaction.from_user_id == user.id,
            BallTransaction.kind.in_((BallTxKind.TRANSFER, BallTxKind.GIFT)),
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
    to_pharmacy: Pharmacy | None = None,
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
        to_pharmacy_id=to_pharmacy.id if to_pharmacy else None,
    )
    session.add(tx)
    await session.flush()
    await log_action(session, sender, "ball_transfer_created", "ball_tx", str(tx.id), f"{kind.value} {amount}")
    return tx


async def create_ball_gift(
    session: AsyncSession, *, sender: User, doctor: Doctor, amount: int
) -> BallTransaction:
    """Совға: PENDING GIFT — TOP menejer tasdiqlagach yuboruvchidan ayirilib doktorga o'tadi."""
    tx = BallTransaction(
        kind=BallTxKind.GIFT,
        status=BallTxStatus.PENDING,
        amount=amount,
        from_user_id=sender.id,
        to_doctor_id=doctor.id,
    )
    session.add(tx)
    await session.flush()
    await log_action(session, sender, "ball_gift_created", "ball_tx", str(tx.id), f"gift {amount}")
    return tx


async def list_pending_gifts(session: AsyncSession, limit: int = 20) -> list[BallTransaction]:
    """TOP menejer tasdig'ini kutayotgan sovg'alar."""
    return list(
        (
            await session.execute(
                select(BallTransaction)
                .where(
                    BallTransaction.kind == BallTxKind.GIFT,
                    BallTransaction.status == BallTxStatus.PENDING,
                )
                .options(
                    selectinload(BallTransaction.from_user),
                    selectinload(BallTransaction.to_doctor).selectinload(Doctor.bot_user),
                )
                .order_by(BallTransaction.created_at)
                .limit(limit)
            )
        ).scalars()
    )


async def get_ball_transaction(session: AsyncSession, tx_id: int) -> BallTransaction | None:
    result = await session.execute(
        select(BallTransaction)
        .options(
            selectinload(BallTransaction.from_user),
            selectinload(BallTransaction.to_user),
            selectinload(BallTransaction.to_doctor),
            selectinload(BallTransaction.to_pharmacy).selectinload(Pharmacy.bot_user),
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

    if tx.kind in (BallTxKind.TRANSFER, BallTxKind.GIFT):
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
    elif tx.to_pharmacy_id is not None:
        await session.execute(
            sa_update(Pharmacy)
            .where(Pharmacy.id == tx.to_pharmacy_id)
            .values(ball_balance=Pharmacy.ball_balance + tx.amount)
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
    session: AsyncSession,
    *,
    user_id: int | None = None,
    doctor_id: int | None = None,
    pharmacy_id: int | None = None,
) -> int:
    """Joriy ball balansi (atomik UPDATE'lardan keyin ORM obyekt eskirgani uchun)."""
    if user_id is not None:
        value = await session.scalar(select(User.ball_balance).where(User.id == user_id))
    elif doctor_id is not None:
        value = await session.scalar(select(Doctor.ball_balance).where(Doctor.id == doctor_id))
    elif pharmacy_id is not None:
        value = await session.scalar(select(Pharmacy.ball_balance).where(Pharmacy.id == pharmacy_id))
    else:
        value = 0
    return int(value or 0)


async def doctors_for_ball_transfer(session: AsyncSession, rep: User) -> list[Doctor]:
    """Ball yubora oladigan doktorlar: ko'rinish qoidasi bo'yicha, APPROVED, botga ulangan.

    Medvakil => o'zi yaratgan; regional menejer => o'z regionidagi hammasi."""
    scope = (
        Doctor.region_id == rep.region_id
        if rep.role == Role.REGIONAL_MANAGER
        else Doctor.manager_id == rep.id
    )
    result = await session.execute(
        select(Doctor)
        .options(selectinload(Doctor.bot_user))
        .where(
            Doctor.approval_status == ApprovalStatus.APPROVED,
            scope,
            Doctor.user_id.is_not(None),
        )
        .order_by(Doctor.full_name)
    )
    doctors = list(result.scalars())
    return [d for d in doctors if d.bot_user is not None and d.bot_user.telegram_id is not None]


async def ball_scope(session: AsyncSession, actor: User) -> tuple[set[int] | None, set[int] | None]:
    """Ball hisoboti ko'lami: (user_id'lar, doktor_id'lar). (None, None) => cheklovsiz.

    owner/top/product => hammasi;
    medvakil => o'zi + O'ZI YARATGAN doktorlar (ro'yxatdagi ko'rinish bilan bir xil);
    regional => o'zi + region medvakillari + REGION doktorlari.

    Regional uchun doktorlar ataylab REGION bo'yicha: bu JAMOA hisoboti — o'z
    medvakillari qilgan ball o'tkazmalari ko'rinishi kerak (aks holda hisobot
    bo'sh chiqadi). Direktoriyadagi doktor RO'YXATI esa baribir faqat o'zi
    yaratganlari bilan cheklangan (`doctor_visible_to`)."""
    if actor.role in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return None, None

    doctor_filter = (
        Doctor.manager_id == actor.id
        if actor.role == Role.MANAGER
        else Doctor.region_id == actor.region_id
    )
    doctor_ids = set(
        (
            await session.execute(
                select(Doctor.id).where(
                    doctor_filter,
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



# ==================== Doktor kategoriyasi (A/B/C) — SAVDO tezligiga qarab ====================
#
# "Ball qaytishi" = doktorga berilgan ball SOTUV orqali ayirilishi (SALE_DEDUCT).
# Kategoriya har 10 kunlik savdo balli tezligiga qarab (foydalanuvchi qoidasi):
#   >= 1000 ball / 10 kun -> A;  500..1000 -> B;  < 500 -> C.
# Bot belgisi OXIRGI 30 KUN bo'yicha (joriy tezlik); web panelда faoliyat boshidan o'rtacha ham.

CATEGORY_A_THRESHOLD = 1000  # 10 kunlik ball
CATEGORY_B_THRESHOLD = 500


def _as_utc(dt: "datetime | None") -> "datetime | None":
    """Naive datetime'ni UTC-aware qiladi (SQLite naive, Postgres aware qaytaradi)."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def ball_category(per_10_days: float) -> str:
    """10 kunlik savdo balli tezligiga qarab A/B/C."""
    if per_10_days >= CATEGORY_A_THRESHOLD:
        return "A"
    if per_10_days >= CATEGORY_B_THRESHOLD:
        return "B"
    return "C"


async def doctor_returned_ball_map(
    session: AsyncSession, doctor_ids: list[int], *, start: datetime | None = None, end: datetime | None = None
) -> dict[int, int]:
    """Doktorlar bo'yicha davr ichида SOTUV orqali qaytган ball (SALE_DEDUCT yig'indisi)."""
    if not doctor_ids:
        return {}
    query = select(
        BallTransaction.to_doctor_id, func.coalesce(func.sum(BallTransaction.amount), 0)
    ).where(
        BallTransaction.kind == BallTxKind.SALE_DEDUCT,
        BallTransaction.to_doctor_id.in_(doctor_ids),
    )
    if start is not None:
        query = query.where(BallTransaction.created_at >= start)
    if end is not None:
        query = query.where(BallTransaction.created_at <= end)
    query = query.group_by(BallTransaction.to_doctor_id)
    return {doc_id: int(total or 0) for doc_id, total in (await session.execute(query)).all()}


async def attach_doctor_categories(session: AsyncSession, doctors: list) -> None:
    """Har doktorга `_category` (A/B/C) biriktiradi — OXIRGI 30 KUN savdo tezligи bo'yicha.

    Ro'yxatда belgи ko'rsatиш uchun (bitta guruh-so'rov, N ta so'rov emas)."""
    ids = [d.id for d in doctors]
    if not ids:
        return
    since = datetime.now(timezone.utc) - timedelta(days=30)
    returned = await doctor_returned_ball_map(session, ids, start=since)
    for d in doctors:
        per10 = returned.get(d.id, 0) / 3.0  # 30 kun / 3 = 10 kunlik tezlik
        d._category = ball_category(per10)


def _avg_return_days(grants: list[tuple], deductions: list[tuple]) -> float | None:
    """FIFO: har ayirilgan ball eng eski berilган ballга taqqoslаб, o'rtacha "yosh" (kun).

    grants/deductions: (created_at, amount) ro'yxatlarи. Berilmagan (queue bo'sh)
    ball ayirилса — u yoshга hisoblanmaydi (nimadир berilmaган narsани "qaytди" deb bo'lmaydi).
    None => hali hech ball qaytmagan yoki taqqoslab bo'lmaydi."""
    from collections import deque

    queue: deque = deque()  # (grant_date, remaining)
    gi = 0
    grants = sorted(((_as_utc(g[0]), g[1]) for g in grants), key=lambda x: x[0])
    deductions = [(_as_utc(d[0]), d[1]) for d in deductions]
    weighted_days = 0.0
    consumed_total = 0
    for ded_date, ded_amount in sorted(deductions, key=lambda x: x[0]):
        # Ayirish sanasигача berilган barcha grantларни queue'га qo'shamиz.
        while gi < len(grants) and grants[gi][0] <= ded_date:
            queue.append([grants[gi][0], int(grants[gi][1])])
            gi += 1
        need = int(ded_amount)
        while need > 0 and queue:
            grant_date, remaining = queue[0]
            take = min(need, remaining)
            weighted_days += take * max(0, (ded_date - grant_date).days)
            consumed_total += take
            need -= take
            remaining -= take
            if remaining <= 0:
                queue.popleft()
            else:
                queue[0][1] = remaining
    if consumed_total <= 0:
        return None
    return round(weighted_days / consumed_total, 1)


async def doctor_ball_stats(session: AsyncSession, doctor_id: int) -> dict:
    """Bitta doktor uchun to'liq ball statistikasи (karta + web uchun).

    Qaytadi: category, returned_30 (oxirgi 30 kun), per10_30, returned_total,
    lifetime_per10, monthly_return, avg_return_days."""
    now = datetime.now(timezone.utc)
    since30 = now - timedelta(days=30)

    returned_30 = (await doctor_returned_ball_map(session, [doctor_id], start=since30)).get(doctor_id, 0)
    returned_total = (await doctor_returned_ball_map(session, [doctor_id])).get(doctor_id, 0)

    # Faoliyat boshi = doktor YARATILGAN sana ("shu doktor bilan ishlаганimizdan beri").
    # Barqaror va tushunарli; birinchи ball harakatига bog'lasak rate sakraб turardи.
    first = _as_utc(await session.scalar(select(Doctor.created_at).where(Doctor.id == doctor_id)))
    if first is None:  # eski/nuqson yozuv — birinchи ball harakatига tayanamиz
        first = _as_utc(await session.scalar(
            select(func.min(BallTransaction.created_at)).where(BallTransaction.to_doctor_id == doctor_id)
        ))
    days_active = max(1, (now - first).days) if first is not None else 1

    lifetime_per10 = returned_total / days_active * 10
    monthly_return = returned_total / days_active * 30

    # FIFO uchun grantlar (TRANSFER/GIFT, ACCEPTED) va ayirishlar (SALE_DEDUCT).
    grant_rows = (
        await session.execute(
            select(BallTransaction.created_at, BallTransaction.amount).where(
                BallTransaction.to_doctor_id == doctor_id,
                BallTransaction.kind.in_((BallTxKind.TRANSFER, BallTxKind.GIFT)),
                BallTransaction.status == BallTxStatus.ACCEPTED,
            )
        )
    ).all()
    ded_rows = (
        await session.execute(
            select(BallTransaction.created_at, BallTransaction.amount).where(
                BallTransaction.to_doctor_id == doctor_id,
                BallTransaction.kind == BallTxKind.SALE_DEDUCT,
            )
        )
    ).all()

    return {
        "category": ball_category(returned_30 / 3.0),
        "returned_30": int(returned_30),
        "per10_30": round(returned_30 / 3.0, 1),
        "returned_total": int(returned_total),
        "lifetime_per10": round(lifetime_per10, 1),
        "monthly_return": round(monthly_return, 1),
        "avg_return_days": _avg_return_days(list(grant_rows), list(ded_rows)),
    }


async def doctors_ball_overview(
    session: AsyncSession, actor: User, *, start: datetime | None = None, end: datetime | None = None
) -> list[dict]:
    """Web panel: ko'rinadigan doktorlar bo'yicha kategoriya + statistika ro'yxatи."""
    doctors = await list_doctors_visible(session, actor, limit=5000)
    result = []
    for d in doctors:
        stats = await doctor_ball_stats(session, d.id)
        stats["doctor_id"] = d.id
        stats["name"] = d.full_name
        stats["region"] = d.region.name if d.region else None
        stats["region_id"] = d.region_id
        stats["lpu_id"] = d.lpu_id
        stats["lpu"] = d.lpu.name if d.lpu else None
        stats["balance"] = int(d.ball_balance or 0)
        result.append(stats)
    # A -> B -> C, keyin savdo tezligи bo'yicha.
    order = {"A": 0, "B": 1, "C": 2}
    result.sort(key=lambda x: (order.get(x["category"], 3), -x["per10_30"]))
    return result


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
    drug_id: int | None = None,
) -> list[dict]:
    """Sotuv pozitsiyalari (tekis qatorlar) — analitika/Excel uchun.

    Har qator: sana, rep, region, dorixona, doktor, dori, soni, narx, ball, tushum.

    `rep_id` — XODIM filtri: sotuvni kim kiritganига emas, DOKTORNI KIM YARATGANIга
    qarab filtrlaydi (`Doctor.manager_id`). Sabab: "qaysi xodim qancha ishlagani" —
    uning o'z doktorlari bo'yicha o'lchanadi; regional menejer medvakilning doktorига
    sotuv kiritса ham, natija o'sha MEDVAKИЛ hisobiга tushishi kerak.
    Doktorsиз sotuvlar bu filtrда chiqmaydи (egasи yo'q)."""
    doctor_owner = aliased(User)  # doktorni YARATGAN xodim (Sale.rep — sotuvni kiritgan)
    query = (
        select(SaleItem, Sale, User, Region, Pharmacy, Doctor, doctor_owner)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(User, User.id == Sale.rep_id)
        .outerjoin(Region, Region.id == User.region_id)
        .outerjoin(Pharmacy, Pharmacy.id == Sale.pharmacy_id)
        .outerjoin(Doctor, Doctor.id == Sale.doctor_id)
        .outerjoin(doctor_owner, doctor_owner.id == Doctor.manager_id)
        .order_by(desc(SaleItem.created_at))
    )
    if start is not None:
        query = query.where(SaleItem.created_at >= start)
    if end is not None:
        query = query.where(SaleItem.created_at <= end)
    if region_id is not None:
        query = query.where(User.region_id == region_id)
    if rep_id is not None:
        # Xodim = doktor EGASI (uni kim yaratgan), sotuvni kim kiritgani emas.
        query = query.where(Doctor.manager_id == rep_id)
    if drug_id is not None:
        query = query.where(SaleItem.drug_id == drug_id)

    rows: list[dict] = []
    for item, sale, rep, region, pharmacy, doctor, owner in (await session.execute(query)).all():
        price = Decimal(str(item.price or 0))
        rows.append(
            {
                "created_at": item.created_at,
                "sale_id": sale.id,
                "rep_id": rep.id,
                "rep_name": rep.full_name,
                # Doktor egasi — "kim ishladi" kesimi shu bo'yicha (sotuvchи emas).
                "owner_id": owner.id if owner else None,
                "owner_name": owner.full_name if owner else None,
                "region_id": region.id if region else None,
                "region_name": region.name if region else None,
                "pharmacy": pharmacy.name if pharmacy else None,
                "drug_id": item.drug_id,
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
    signed_date: str | None = None,
    new_name: str | None = None,
) -> Contract:
    """Operator tasdig'i: nom tuzatish (ixtiyoriy) + shartnoma raqami/sanasi + APPROVED.

    PDF fayl talab qilinmaydi (faqat raqam va sana)."""
    if new_name:
        pharmacy.name = new_name
    pharmacy.approval_status = ApprovalStatus.APPROVED
    contract = Contract(
        pharmacy_id=pharmacy.id,
        number=contract_number,
        signed_date=signed_date,
        status=ContractStatus.ACTIVE,
        requested_by_id=operator.id,
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


# ==================== Owner hisobot drill-down ====================


async def list_report_authors(
    session: AsyncSession, *, role: Role, region_id: int | None = None, limit: int = 300
) -> list[User]:
    """Berilgan roldagi (ixtiyoriy region bilan) faol xodimlar — hisobot mualliflari."""
    query = (
        select(User)
        .options(selectinload(User.region))
        .where(User.role == role, User.is_active.is_(True))
        .order_by(User.full_name)
        .limit(limit)
    )
    if region_id is not None:
        query = query.where(User.region_id == region_id)
    return list((await session.execute(query)).scalars())


async def get_active_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.region)).where(User.id == user_id, User.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def get_user_full(session: AsyncSession, user_id: int) -> User | None:
    """Foydalanuvchi + region (faol/nofaol — detail karta uchun)."""
    result = await session.execute(
        select(User).options(selectinload(User.region)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def set_user_active(session: AsyncSession, *, user: User, active: bool, actor: User) -> None:
    """Xodimni faolsizlantirish/faollashtirish (soft delete — tarix saqlanadi)."""
    user.is_active = active
    await session.flush()
    await log_action(
        session, actor, "user_activated" if active else "user_deactivated",
        "user", str(user.id), user.full_name,
    )


async def edit_user(
    session: AsyncSession,
    *,
    user: User,
    actor: User,
    full_name: str | None = None,
    phone_number: str | None = None,
    role: "Role | None" = None,
    region_id: int | None = None,
) -> None:
    """Xodim ma'lumotlarini tahrirlash (owner). Faqat berilgan maydonlar yangilanadi."""
    changes: list[str] = []
    if full_name is not None:
        user.full_name = full_name
        changes.append("full_name")
    if phone_number is not None:
        user.phone_number = phone_number
        changes.append("phone")
    if role is not None:
        user.role = role
        changes.append(f"role={role.value}")
    if region_id is not None:
        user.region_id = region_id
        changes.append(f"region={region_id}")
    await session.flush()
    await log_action(session, actor, "user_edited", "user", str(user.id), ", ".join(changes) or "-")


async def delete_user(session: AsyncSession, *, user: User, actor: User) -> None:
    """Xodimni BUTUNLAY o'chirish. FK CASCADE tufayli bog'liq sotuv/hisobot/oylik/
    zayavkalar ham o'chadi (Postgres). Qaytarib bo'lmaydi."""
    await log_action(session, actor, "user_deleted", "user", str(user.id), user.full_name)
    await session.delete(user)
    await session.flush()


async def reports_by_author(
    session: AsyncSession,
    author_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
) -> list[DailyReport]:
    query = (
        select(DailyReport)
        .options(selectinload(DailyReport.doctor), selectinload(DailyReport.pharmacy))
        .where(DailyReport.author_id == author_id)
        .order_by(desc(DailyReport.created_at))
        .limit(limit)
    )
    if start is not None:
        query = query.where(DailyReport.created_at >= start)
    if end is not None:
        query = query.where(DailyReport.created_at <= end)
    return list((await session.execute(query)).scalars())


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

