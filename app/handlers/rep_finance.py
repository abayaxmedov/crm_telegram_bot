from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, User
from app.db.repositories import (
    get_doctor,
    list_doctors_with_bonus,
    pay_doctor_bonus,
    return_to_admin,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user
from app.i18n import month_name, t, variants
from app.keyboards.reply import entities_inline, main_menu, rep_finance_menu
from app.services.kpi import compute_kpi

router = Router(name="rep_finance")


class PayFlow(StatesGroup):
    amount = State()


class ReturnFlow(StatesGroup):
    amount = State()


def _money(value) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


def _region(rep: User, lang: str) -> str:
    parts = [p for p in (rep.region_city, rep.region_rayon) if p]
    return ", ".join(parts) if parts else t(lang, "region_unset")


def _parse_amount(value: str | None) -> Decimal | None:
    try:
        return Decimal((value or "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None


# ==================== Финансы ====================

@router.message(F.text.in_(variants("btn_finance")), RoleFilter(Role.MANAGER))
async def rep_finance_panel(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    await state.clear()
    await message.answer(
        t(lang, "rep_finance_header", name=rep.full_name, region=_region(rep, lang), balance=_money(rep.balance)),
        reply_markup=rep_finance_menu(lang),
    )


@router.message(F.text.in_(variants("btn_pay_doctor")), RoleFilter(Role.MANAGER))
async def pay_start(message: Message, session: AsyncSession, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    doctors = await list_doctors_with_bonus(session, rep)
    if not doctors:
        await message.answer(t(lang, "pay_no_doctors"), reply_markup=rep_finance_menu(lang))
        return
    await message.answer(
        t(lang, "pay_choose_doctor", balance=_money(rep.balance)),
        reply_markup=entities_inline(
            [(d.id, f"{d.full_name} ({_money(d.bonus_balance)})") for d in doctors], "pay_doc"
        ),
    )


@router.callback_query(F.data.startswith("pay_doc:"))
async def pay_pick_doctor(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_callback_user(callback, session)
    if rep is None:
        return
    doctor = await get_doctor(session, int(callback.data.split(":", 1)[1]))
    if doctor is None:
        await callback.answer()
        return
    await state.update_data(doctor_id=doctor.id)
    await state.set_state(PayFlow.amount)
    await callback.message.answer(
        t(
            lang,
            "pay_doctor_selected",
            doctor=doctor.full_name,
            doc_balance=_money(doctor.bonus_balance),
            balance=_money(rep.balance),
        )
    )
    await callback.answer()


@router.message(PayFlow.amount)
async def pay_amount(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    amount = _parse_amount(message.text)
    if amount is None or amount <= 0:
        await message.answer(t(lang, "amount_invalid"))
        return
    rep = await require_user(message, session)
    if rep is None:
        return
    data = await state.get_data()
    doctor = await get_doctor(session, data.get("doctor_id"))
    if doctor is None:
        await state.clear()
        return
    if amount > (rep.balance or Decimal("0")):
        await message.answer(t(lang, "pay_insufficient", balance=_money(rep.balance)))
        return
    if amount > (doctor.bonus_balance or Decimal("0")):
        await message.answer(t(lang, "pay_over_doctor_bonus", doc_balance=_money(doctor.bonus_balance)))
        return

    await pay_doctor_bonus(session, rep=rep, doctor=doctor, amount=amount)
    await session.commit()
    await state.clear()
    await message.answer(
        t(
            lang,
            "pay_done",
            doctor=doctor.full_name,
            amount=_money(amount),
            balance=_money(rep.balance),
            doc_balance=_money(doctor.bonus_balance),
        ),
        reply_markup=rep_finance_menu(lang),
    )


@router.message(F.text.in_(variants("btn_return_admin")), RoleFilter(Role.MANAGER))
async def return_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    if (rep.balance or Decimal("0")) <= 0:
        await message.answer(t(lang, "return_zero"), reply_markup=rep_finance_menu(lang))
        return
    await state.set_state(ReturnFlow.amount)
    await message.answer(t(lang, "return_enter_amount", balance=_money(rep.balance)))


@router.message(ReturnFlow.amount)
async def return_amount(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    amount = _parse_amount(message.text)
    if amount is None or amount <= 0:
        await message.answer(t(lang, "amount_invalid"))
        return
    rep = await require_user(message, session)
    if rep is None:
        return
    if amount > (rep.balance or Decimal("0")):
        await message.answer(t(lang, "pay_insufficient", balance=_money(rep.balance)))
        return
    await return_to_admin(session, rep=rep, amount=amount)
    await session.commit()
    await state.clear()
    await message.answer(
        t(lang, "return_done", amount=_money(amount), balance=_money(rep.balance)),
        reply_markup=rep_finance_menu(lang),
    )


# ==================== Моя зарплата (KPI) ====================

@router.message(F.text.in_(variants("btn_salary")), RoleFilter(Role.MANAGER))
async def rep_salary(message: Message, session: AsyncSession, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    await message.answer(t(lang, "kpi_calculating"))

    results, buckets, total = await compute_kpi(session, rep)
    now = datetime.utcnow()
    header = t(lang, "kpi_header", month=month_name(lang, now.month, now.year), name=rep.full_name)

    if not results:
        await message.answer(header + "\n\n" + t(lang, "kpi_no_plans"), reply_markup=main_menu(rep.role, lang))
        return

    blocks = "\n\n".join(t(lang, "kpi_drug_block", **r) for r in results)
    footer = t(
        lang,
        "kpi_footer",
        b1=_money(buckets[1]),
        b3=_money(buckets[3]),
        b6=_money(buckets[6]),
        total=_money(total),
    )
    await message.answer(
        header + "\n\n" + blocks + "\n\n" + "━" * 12 + "\n" + footer,
        reply_markup=main_menu(rep.role, lang),
    )
