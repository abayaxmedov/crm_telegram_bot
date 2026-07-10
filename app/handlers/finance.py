from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FinanceType, Role
from app.db.repositories import (
    add_finance_operation,
    list_finance_operations,
    period_window,
    sales_item_rows,
)
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.i18n import finance_label, t, variants
from app.keyboards.reply import excel_periods_keyboard, finance_menu, finance_type_keyboard
from app.services.excel import build_xlsx
from app.services.media import answer_media
from app.services.security import can_add_finance_operation, can_view_finance_report

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
    if not can_view_finance_report(user.role):
        await message.answer(t(lang, "finance_owner_only"))
        return
    await answer_media(
        message,
        screen="finance",
        text=t(lang, "finance_text"),
        lang=lang,
        reply_markup=finance_menu(lang, is_owner=user.role == Role.OWNER),
    )


@router.message(F.text.in_(variants("btn_finance_add")))
async def finance_start(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_add_finance_operation(user.role):
        await message.answer(t(lang, "no_perm_finance_op"))
        return
    await message.answer(t(lang, "choose_op_type"), reply_markup=finance_type_keyboard(lang))


@router.callback_query(F.data.startswith("finance_type:"))
async def finance_type(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_add_finance_operation(user.role):
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
    if not can_view_finance_report(user.role):
        await message.answer(t(lang, "finance_report_owner_only"))
        return

    operations = await list_finance_operations(session)
    totals = {operation_type: Decimal("0") for operation_type in FinanceType}
    for operation in operations:
        totals[operation.operation_type] += operation.amount

    # Sotuv tushumi ham moliyaviy hisobotning bir qismi (30 kunlik ko'rsatkich).
    start, end = period_window("30d")
    sale_rows = await sales_item_rows(session, start=start, end=end)
    revenue_30d = sum((r["revenue"] for r in sale_rows), Decimal("0"))

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
    text += (latest or "-")
    text += f"\n\n🛍 {t(lang, 'report_sec_sales')} ({t(lang, 'period_30d')}): {revenue_30d:,.2f}"
    await message.answer(text, reply_markup=excel_periods_keyboard(lang, "fin_xlsx"))


@router.callback_query(F.data.startswith("fin_xlsx:"))
async def finance_report_xlsx(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_finance_report(user.role):
        await callback.answer(t(lang, "no_perm_generic"), show_alert=True)
        return

    await callback.answer()
    period = callback.data.split(":", 1)[1]
    start, end = period_window(period)

    operations = await list_finance_operations(session, limit=5000, start=start, end=end)
    totals = {operation_type: Decimal("0") for operation_type in FinanceType}
    for operation in operations:
        totals[operation.operation_type] += operation.amount

    op_rows = [
        [
            o.id,
            str(o.created_at)[:16],
            finance_label(lang, o.operation_type),
            o.amount,
            o.title,
            o.description,
        ]
        for o in operations
    ]

    sale_rows_raw = await sales_item_rows(session, start=start, end=end)
    revenue = sum((r["revenue"] for r in sale_rows_raw), Decimal("0"))
    total_ball = sum(r["ball_total"] for r in sale_rows_raw)
    sale_rows = [
        [
            str(r["created_at"])[:16],
            r["rep_name"],
            r["region_name"],
            r["pharmacy"],
            r["doctor"],
            r["drug_name"],
            r["qty"],
            r["price"],
            r["revenue"],
            r["ball_total"],
        ]
        for r in sale_rows_raw
    ]

    summary_rows = [
        [t(lang, "fin_income"), totals[FinanceType.INCOME]],
        [t(lang, "fin_expense"), totals[FinanceType.EXPENSE]],
        [t(lang, "fin_debt"), totals[FinanceType.DEBT]],
        [t(lang, "fin_payment"), totals[FinanceType.PAYMENT]],
        [t(lang, "report_sec_sales"), revenue],
        ["💠 Ball", total_ball],
    ]

    data = build_xlsx(
        [
            ("Жами", ["Кўрсаткич", "Сумма"], summary_rows),
            ("Операциялар", ["ID", "Сана", "Тури", "Сумма", "Номи", "Изоҳ"], op_rows),
            (
                "Сотув тушуми",
                ["Сана", "Сотувчи", "Регион", "Дорихона", "Доктор", "Препарат", "Упак.", "Нарх", "Тушум", "Балл"],
                sale_rows,
            ),
        ]
    )
    await callback.message.answer_document(
        document=BufferedInputFile(data, filename=f"finance_report_{period}.xlsx"),
        caption=t(lang, "excel_caption_finance", period=t(lang, f"period_{period}")),
    )
