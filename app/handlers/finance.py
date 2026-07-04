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
from app.i18n import finance_label, t, variants
from app.keyboards.reply import finance_menu, finance_type_keyboard
from app.services.media import answer_media
from app.services.security import can_view_finance

router = Router(name="finance")


class FinanceFlow(StatesGroup):
    amount = State()
    title = State()
    description = State()


@router.message(F.text.in_(variants("btn_finance")))
async def finance_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await message.answer(t(lang, "finance_owner_only"))
        return
    await answer_media(message, screen="finance", text=t(lang, "finance_text"), lang=lang, reply_markup=finance_menu(lang))


@router.message(F.text.in_(variants("btn_finance_add")))
async def finance_start(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await message.answer(t(lang, "no_perm_finance_op"))
        return
    await message.answer(t(lang, "choose_op_type"), reply_markup=finance_type_keyboard(lang))


@router.callback_query(F.data.startswith("finance_type:"))
async def finance_type(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await callback.answer(t(lang, "no_perm_generic"), show_alert=True)
        return
    operation_type = FinanceType(callback.data.split(":", 1)[1])
    await state.update_data(operation_type=operation_type.value)
    await state.set_state(FinanceFlow.amount)
    await callback.message.answer(t(lang, "enter_amount"))
    await callback.answer()


@router.message(FinanceFlow.amount)
async def finance_amount(message: Message, state: FSMContext, lang: str) -> None:
    try:
        amount = Decimal((message.text or "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        await message.answer(t(lang, "amount_invalid"))
        return
    if amount <= 0:
        await message.answer(t(lang, "amount_gt_zero"))
        return
    await state.update_data(amount=str(amount))
    await state.set_state(FinanceFlow.title)
    await message.answer(t(lang, "enter_op_name"))


@router.message(FinanceFlow.title)
async def finance_title(message: Message, state: FSMContext, lang: str) -> None:
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer(t(lang, "name_too_short"))
        return
    await state.update_data(title=title)
    await state.set_state(FinanceFlow.description)
    await message.answer(t(lang, "enter_extra_desc"))


@router.message(FinanceFlow.description)
async def finance_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
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
        text=t(lang, "finance_op_saved", id=operation.id, title=escape(operation.title)),
        lang=lang,
        reply_markup=finance_menu(lang),
    )


@router.message(F.text.in_(variants("btn_finance_report")))
async def finance_report(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_finance(user.role):
        await message.answer(t(lang, "finance_report_owner_only"))
        return

    operations = await list_finance_operations(session)
    totals = {operation_type: Decimal("0") for operation_type in FinanceType}
    for operation in operations:
        totals[operation.operation_type] += operation.amount

    text = t(
        lang,
        "finance_report",
        income=f"{totals[FinanceType.INCOME]:,.2f}",
        expense=f"{totals[FinanceType.EXPENSE]:,.2f}",
        debt=f"{totals[FinanceType.DEBT]:,.2f}",
        payment=f"{totals[FinanceType.PAYMENT]:,.2f}",
    )
    latest = "\n".join(
        f"#{operation.id} | {finance_label(lang, operation.operation_type)} | {operation.amount:,.2f} | {safe(operation.title)}"
        for operation in operations[:10]
    )
    await message.answer(text + (latest or "-"), reply_markup=finance_menu(lang))
