from __future__ import annotations

"""Preparatlar (tovarlar) bo'limi — narx va aksiya ballini faqat OWNER kiritadi."""

from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_drug, get_drug, list_all_drugs, update_drug
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import drugs_menu
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import can_manage_drugs

router = Router(name="drugs_admin")


class DrugAddFlow(StatesGroup):
    name = State()
    price = State()
    ball = State()


class DrugEditFlow(StatesGroup):
    price = State()
    ball = State()


def _parse_price(value: str | None) -> Decimal | None:
    try:
        amount = Decimal((value or "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None
    return amount if amount >= 0 else None


def _drug_line(lang: str, drug) -> str:
    return t(
        lang,
        "drug_row",
        id=drug.id,
        name=safe(drug.name),
        price=f"{drug.price or 0:,.2f}",
        ball=int(drug.ball or 0),
    )


@router.message(F.text.in_(variants("btn_drugs")))
async def drugs_panel(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_drugs(user.role):
        await message.answer(t(lang, "no_perm_drugs"))
        return
    await state.clear()
    await answer_media(message, screen="admin", text=t(lang, "drugs_text"), lang=lang, reply_markup=drugs_menu(lang))


# ==================== Qo'shish ====================


@router.message(F.text.in_(variants("btn_drug_add")))
async def drug_add_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_drugs(user.role):
        await message.answer(t(lang, "no_perm_drugs"))
        return
    await state.set_state(DrugAddFlow.name)
    await message.answer(t(lang, "enter_drug_name"))


@router.message(DrugAddFlow.name)
async def drug_add_name(message: Message, state: FSMContext, lang: str) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer(t(lang, "name_too_short"))
        return
    await state.update_data(name=name)
    await state.set_state(DrugAddFlow.price)
    await message.answer(t(lang, "enter_drug_price"))


@router.message(DrugAddFlow.price)
async def drug_add_price(message: Message, state: FSMContext, lang: str) -> None:
    price = _parse_price(message.text)
    if price is None:
        await message.answer(t(lang, "price_invalid"))
        return
    await state.update_data(price=str(price))
    await state.set_state(DrugAddFlow.ball)
    await message.answer(t(lang, "enter_drug_ball"))


@router.message(DrugAddFlow.ball)
async def drug_add_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_drugs(user.role):
        await state.clear()
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(t(lang, "ball_amount_invalid"))
        return

    data = await state.get_data()
    drug = await add_drug(session, name=data["name"], price=Decimal(data["price"]), ball=int(raw), actor=user)
    await session.commit()
    await state.clear()
    await message.answer(
        t(
            lang,
            "drug_saved",
            id=drug.id,
            name=escape(drug.name),
            price=f"{drug.price:,.2f}",
            ball=int(drug.ball or 0),
        ),
        reply_markup=drugs_menu(lang),
    )


# ==================== Ro'yxat ====================


@router.message(F.text.in_(variants("btn_drugs_list")))
async def drugs_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_drugs(user.role):
        await message.answer(t(lang, "no_perm_drugs"))
        return
    drugs = await list_all_drugs(session)
    if not drugs:
        await message.answer(t(lang, "drugs_empty"), reply_markup=drugs_menu(lang))
        return
    text = t(lang, "drugs_header") + "\n\n" + "\n".join(_drug_line(lang, d) for d in drugs)
    await message.answer(text, reply_markup=drugs_menu(lang))


# ==================== Tahrirlash ====================


@router.message(F.text.in_(variants("btn_drug_edit")))
async def drug_edit_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_drugs(user.role):
        await message.answer(t(lang, "no_perm_drugs"))
        return
    await show_list(message, session, user, lang, state, "drug_edit")


@router.callback_query(F.data.startswith("drug_edit:"))
async def drug_edit_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_manage_drugs(user.role):
        await callback.answer(t(lang, "no_perm_drugs"), show_alert=True)
        return
    drug = await get_drug(session, int(callback.data.split(":", 1)[1]))
    if drug is None:
        await callback.answer()
        return
    await state.update_data(drug_id=drug.id)
    await state.set_state(DrugEditFlow.price)
    await callback.message.answer(t(lang, "enter_drug_price"))
    await callback.answer()


@router.message(DrugEditFlow.price)
async def drug_edit_price(message: Message, state: FSMContext, lang: str) -> None:
    price = _parse_price(message.text)
    if price is None:
        await message.answer(t(lang, "price_invalid"))
        return
    await state.update_data(price=str(price))
    await state.set_state(DrugEditFlow.ball)
    await message.answer(t(lang, "enter_drug_ball"))


@router.message(DrugEditFlow.ball)
async def drug_edit_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_drugs(user.role):
        await state.clear()
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(t(lang, "ball_amount_invalid"))
        return

    data = await state.get_data()
    drug = await get_drug(session, data.get("drug_id"))
    if drug is None:
        await state.clear()
        return
    await update_drug(session, drug=drug, price=Decimal(data["price"]), ball=int(raw), actor=user)
    await session.commit()
    await state.clear()
    await message.answer(
        t(
            lang,
            "drug_updated",
            name=escape(drug.name),
            price=f"{drug.price:,.2f}",
            ball=int(drug.ball or 0),
        ),
        reply_markup=drugs_menu(lang),
    )
