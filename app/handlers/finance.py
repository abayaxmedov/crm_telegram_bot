from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FinanceType
from app.db.repositories import add_finance_operation, list_finance_operations
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.keyboards.reply import BTN_FINANCE, finance_menu, finance_type_keyboard
from app.services.media import answer_media
from app.services.security import can_view_finance
from app.texts import FINANCE_TEXT

router = Router(name="finance")


class FinanceFlow(StatesGroup):
    amount = State()
    title = State()
    description = State()


@router.message(F.text == BTN_FINANCE)
async def finance_panel(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await message.answer("Finans bo'limi faqat owner uchun ochiq.")
        return
    await answer_media(message, screen="finance", text=FINANCE_TEXT, reply_markup=finance_menu())


@router.message(F.text == "➕ Finans operatsiya")
async def finance_start(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await message.answer("Finans operatsiya uchun ruxsat yo'q.")
        return
    await message.answer("Operatsiya turini tanlang:", reply_markup=finance_type_keyboard())


@router.callback_query(F.data.startswith("finance_type:"))
async def finance_type(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
    operation_type = FinanceType(callback.data.split(":", 1)[1])
    await state.update_data(operation_type=operation_type.value)
    await state.set_state(FinanceFlow.amount)
    await callback.message.answer("Summani kiriting. Masalan: 1250000")
    await callback.answer()


@router.message(FinanceFlow.amount)
async def finance_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        await message.answer("Summa noto'g'ri. Faqat raqam yuboring.")
        return
    if amount <= 0:
        await message.answer("Summa 0 dan katta bo'lsin.")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(FinanceFlow.title)
    await message.answer("Operatsiya nomi:")


@router.message(FinanceFlow.title)
async def finance_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer("Nom juda qisqa.")
        return
    await state.update_data(title=title)
    await state.set_state(FinanceFlow.description)
    await message.answer("Qo'shimcha tavsif. Kerak bo'lmasa `-` yuboring:")


@router.message(FinanceFlow.description)
async def finance_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    data = await state.get_data()
    operation = await add_finance_operation(
        session,
        operation_type=FinanceType(data["operation_type"]),
        amount=Decimal(data["amount"]),
        title=data["title"],
        description=clean_optional(message.text),
        created_by=user,
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=f"<b>Finans operatsiya saqlandi:</b> #{operation.id} {escape(operation.title)}",
        reply_markup=finance_menu(),
    )


@router.message(F.text == "📊 Finans hisobot")
async def finance_report(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await message.answer("Finans hisobot faqat owner uchun ochiq.")
        return

    operations = await list_finance_operations(session)
    totals = {operation_type: Decimal("0") for operation_type in FinanceType}
    for operation in operations:
        totals[operation.operation_type] += operation.amount

    text = (
        "<b>Finans hisobot</b>\n\n"
        f"Kirim: {totals[FinanceType.INCOME]:,.2f}\n"
        f"Chiqim: {totals[FinanceType.EXPENSE]:,.2f}\n"
        f"Qarzdorlik: {totals[FinanceType.DEBT]:,.2f}\n"
        f"To'lov: {totals[FinanceType.PAYMENT]:,.2f}\n\n"
        "<b>Oxirgi operatsiyalar</b>\n"
    )
    latest = "\n".join(
        f"#{operation.id} | {operation.operation_type.value} | {operation.amount:,.2f} | {safe(operation.title)}"
        for operation in operations[:10]
    )
    await message.answer(text + (latest or "-"), reply_markup=finance_menu())

