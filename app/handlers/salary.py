from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, User
from app.db.repositories import add_salary, list_salaries_for_user
from app.handlers.utils import require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import salary_menu
from app.services.media import answer_media

router = Router(name="salary")


class SalaryFlow(StatesGroup):
    telegram_id = State()
    month = State()
    base = State()
    bonus = State()
    penalty = State()


@router.message(F.text.in_(variants("btn_salary")))
async def salary_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(
        message,
        screen="salary",
        text=t(lang, "salary_text"),
        lang=lang,
        reply_markup=salary_menu(lang, is_owner=user.role == Role.OWNER),
    )


@router.message(F.text.in_(variants("btn_salary_my")))
async def my_salary(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    salaries = await list_salaries_for_user(session, user)
    if not salaries:
        await message.answer(
            t(lang, "salary_empty_user"), reply_markup=salary_menu(lang, is_owner=user.role == Role.OWNER)
        )
        return

    text = t(lang, "salary_my_header") + "\n\n" + "\n".join(
        f"{safe(row.month)} | {t(lang, 'salary_base')}: {row.base_salary:,.2f} | "
        f"{t(lang, 'salary_bonus')}: {row.bonus:,.2f} | {t(lang, 'salary_penalty')}: {row.penalty:,.2f} | "
        f"{t(lang, 'salary_total')}: {row.total_amount:,.2f} | {safe(row.status)}"
        for row in salaries
    )
    await message.answer(text, reply_markup=salary_menu(lang, is_owner=user.role == Role.OWNER))


@router.message(F.text.in_(variants("btn_salary_add")))
async def salary_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role != Role.OWNER:
        await message.answer(t(lang, "salary_owner_only"))
        return
    await state.set_state(SalaryFlow.telegram_id)
    await message.answer(t(lang, "enter_user_tg_id"))


@router.message(SalaryFlow.telegram_id)
async def salary_user(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    try:
        telegram_id = int((message.text or "").strip())
    except ValueError:
        await message.answer(t(lang, "tg_id_must_be_number"))
        return

    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        await message.answer(t(lang, "tg_id_not_found"))
        return

    await state.update_data(user_id=user.id)
    await state.set_state(SalaryFlow.month)
    await message.answer(t(lang, "enter_month"))


@router.message(SalaryFlow.month)
async def salary_month(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(month=(message.text or "").strip())
    await state.set_state(SalaryFlow.base)
    await message.answer(t(lang, "enter_base_salary"))


@router.message(SalaryFlow.base)
async def salary_base(message: Message, state: FSMContext, lang: str) -> None:
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(t(lang, "amount_invalid_simple"))
        return
    await state.update_data(base=str(amount))
    await state.set_state(SalaryFlow.bonus)
    await message.answer(t(lang, "enter_bonus"))


@router.message(SalaryFlow.bonus)
async def salary_bonus(message: Message, state: FSMContext, lang: str) -> None:
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer(t(lang, "amount_invalid_simple"))
        return
    await state.update_data(bonus=str(amount))
    await state.set_state(SalaryFlow.penalty)
    await message.answer(t(lang, "enter_penalty"))


@router.message(SalaryFlow.penalty)
async def salary_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    actor = await require_user(message, session)
    if actor is None:
        return

    penalty = parse_amount(message.text)
    if penalty is None:
        await message.answer(t(lang, "amount_invalid_simple"))
        return

    data = await state.get_data()
    result = await session.execute(select(User).where(User.id == data["user_id"]))
    user = result.scalar_one()
    salary = await add_salary(
        session,
        user=user,
        month=data["month"],
        base_salary=Decimal(data["base"]),
        bonus=Decimal(data["bonus"]),
        penalty=penalty,
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=t(lang, "salary_saved", name=safe(user.full_name), total=f"{salary.total_amount:,.2f}"),
        lang=lang,
        reply_markup=salary_menu(lang, is_owner=True),
    )


def parse_amount(value: str | None) -> Decimal | None:
    try:
        amount = Decimal((value or "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None
    return amount if amount >= 0 else None
