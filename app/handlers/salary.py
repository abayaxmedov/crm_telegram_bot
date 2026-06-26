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
from app.keyboards.reply import BTN_SALARY, salary_menu
from app.services.media import answer_media
from app.texts import SALARY_TEXT

router = Router(name="salary")


class SalaryFlow(StatesGroup):
    telegram_id = State()
    month = State()
    base = State()
    bonus = State()
    penalty = State()


@router.message(F.text == BTN_SALARY)
async def salary_panel(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(
        message,
        screen="salary",
        text=SALARY_TEXT,
        reply_markup=salary_menu(is_owner=user.role == Role.OWNER),
    )


@router.message(F.text == "📋 Mening zarplatam")
async def my_salary(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    salaries = await list_salaries_for_user(session, user)
    if not salaries:
        await message.answer("Siz uchun zarplata yozuvlari hali yo'q.", reply_markup=salary_menu(user.role == Role.OWNER))
        return

    text = "<b>Mening zarplatam</b>\n\n" + "\n".join(
        f"{safe(row.month)} | asosiy: {row.base_salary:,.2f} | bonus: {row.bonus:,.2f} | "
        f"jarima: {row.penalty:,.2f} | jami: {row.total_amount:,.2f} | {safe(row.status)}"
        for row in salaries
    )
    await message.answer(text, reply_markup=salary_menu(user.role == Role.OWNER))


@router.message(F.text == "➕ Zarplata kiritish")
async def salary_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role != Role.OWNER:
        await message.answer("Zarplata kiritish faqat owner uchun ochiq.")
        return
    await state.set_state(SalaryFlow.telegram_id)
    await message.answer("User Telegram ID sini kiriting:")


@router.message(SalaryFlow.telegram_id)
async def salary_user(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        telegram_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Telegram ID raqam bo'lishi kerak.")
        return

    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        await message.answer("Bu Telegram ID bazada topilmadi.")
        return

    await state.update_data(user_id=user.id)
    await state.set_state(SalaryFlow.month)
    await message.answer("Oy nomi. Masalan: Iyun 2026")


@router.message(SalaryFlow.month)
async def salary_month(message: Message, state: FSMContext) -> None:
    await state.update_data(month=(message.text or "").strip())
    await state.set_state(SalaryFlow.base)
    await message.answer("Asosiy oylik:")


@router.message(SalaryFlow.base)
async def salary_base(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer("Summa noto'g'ri.")
        return
    await state.update_data(base=str(amount))
    await state.set_state(SalaryFlow.bonus)
    await message.answer("Bonus:")


@router.message(SalaryFlow.bonus)
async def salary_bonus(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer("Summa noto'g'ri.")
        return
    await state.update_data(bonus=str(amount))
    await state.set_state(SalaryFlow.penalty)
    await message.answer("Jarima:")


@router.message(SalaryFlow.penalty)
async def salary_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    actor = await require_user(message, session)
    if actor is None:
        return

    penalty = parse_amount(message.text)
    if penalty is None:
        await message.answer("Summa noto'g'ri.")
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
        text=f"<b>Zarplata saqlandi:</b> {safe(user.full_name)} | {salary.total_amount:,.2f}",
        reply_markup=salary_menu(is_owner=True),
    )


def parse_amount(value: str | None) -> Decimal | None:
    try:
        amount = Decimal((value or "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None
    return amount if amount >= 0 else None

