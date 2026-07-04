from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Pharmacy, Role
from app.db.repositories import (
    create_sale,
    get_doctor,
    get_drug,
    get_pharmacy,
    list_active_drugs,
    list_doctors_for_manager,
    list_pharmacies_for_manager,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user
from app.i18n import t, variants
from app.keyboards.reply import entities_inline, main_menu, sale_cart_keyboard
from app.services.media import answer_media

router = Router(name="sales")


class SalesFlow(StatesGroup):
    qty = State()


def _num(value) -> str:
    d = Decimal(str(value))
    return str(int(d)) if d == d.to_integral_value() else f"{d:.2f}"


def _ph_label(pharmacy: Pharmacy) -> str:
    if pharmacy.filial:
        return f"{pharmacy.name} (Филиал: {pharmacy.filial})"
    return pharmacy.name


def _cart_text(lang: str, cart: list[dict]) -> str:
    lines = [f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')}." for i, c in enumerate(cart, 1)]
    return t(lang, "cart_title") + "\n" + "\n".join(lines)


async def _send_drug_choice(message: Message, session: AsyncSession, lang: str) -> None:
    drugs = await list_active_drugs(session)
    if not drugs:
        await message.answer(t(lang, "sales_no_drugs"))
        return
    items = [(d.id, f"{d.name} ({t(lang, 'stock_short')}: {d.stock} {t(lang, 'pcs')})") for d in drugs]
    await message.answer(t(lang, "sales_choose_drug"), reply_markup=entities_inline(items, "sale_drug"))


@router.message(F.text.in_(variants("btn_sales")), RoleFilter(Role.MANAGER))
async def sales_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    pharmacies = await list_pharmacies_for_manager(session, rep)
    if not pharmacies:
        await message.answer(t(lang, "sales_no_pharmacies"))
        return
    await state.clear()
    await message.answer(
        t(lang, "sales_choose_pharmacy"),
        reply_markup=entities_inline([(p.id, _ph_label(p)) for p in pharmacies], "sale_ph"),
    )


@router.callback_query(F.data.startswith("sale_ph:"))
async def sale_pick_pharmacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_callback_user(callback, session)
    if rep is None:
        return
    pharmacy_id = int(callback.data.split(":", 1)[1])
    doctors = await list_doctors_for_manager(session, rep)
    if not doctors:
        await callback.message.answer(t(lang, "sales_no_doctors"))
        await callback.answer()
        return
    await state.update_data(pharmacy_id=pharmacy_id, cart=[])
    await callback.message.answer(
        t(lang, "sales_choose_doctor"),
        reply_markup=entities_inline([(d.id, d.full_name) for d in doctors], "sale_doc"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sale_doc:"))
async def sale_pick_doctor(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_callback_user(callback, session)
    if rep is None:
        return
    await state.update_data(doctor_id=int(callback.data.split(":", 1)[1]))
    await _send_drug_choice(callback.message, session, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("sale_drug:"))
async def sale_pick_drug(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_callback_user(callback, session)
    if rep is None:
        return
    drug = await get_drug(session, int(callback.data.split(":", 1)[1]))
    if drug is None:
        await callback.answer()
        return
    await state.update_data(current_drug_id=drug.id)
    await state.set_state(SalesFlow.qty)
    await callback.message.answer(t(lang, "sales_drug_info", name=drug.name, stock=drug.stock))
    await callback.answer()


@router.message(SalesFlow.qty)
async def sale_qty(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(t(lang, "qty_invalid"))
        return
    qty = int(raw)
    data = await state.get_data()
    drug = await get_drug(session, data.get("current_drug_id"))
    if drug is None:
        await state.set_state(None)
        return
    if qty > drug.stock:
        await message.answer(t(lang, "qty_over_stock", stock=drug.stock))
        return

    cart = data.get("cart", [])
    cart.append({"drug_id": drug.id, "name": drug.name, "qty": qty, "rate": str(drug.doctor_bonus_per_pack)})
    await state.update_data(cart=cart)
    await state.set_state(None)
    await message.answer(_cart_text(lang, cart), reply_markup=sale_cart_keyboard(lang))


@router.callback_query(F.data == "sale_cart:add")
async def sale_cart_add(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    if await require_callback_user(callback, session) is None:
        return
    await _send_drug_choice(callback.message, session, lang)
    await callback.answer()


@router.callback_query(F.data == "sale_cart:finish")
async def sale_cart_finish(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_callback_user(callback, session)
    if rep is None:
        return
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await callback.answer(t(lang, "cart_empty"), show_alert=True)
        return

    pharmacy = await get_pharmacy(session, data["pharmacy_id"]) if data.get("pharmacy_id") else None
    doctor = await get_doctor(session, data["doctor_id"]) if data.get("doctor_id") else None

    items = []
    for entry in cart:
        drug = await get_drug(session, entry["drug_id"])
        if drug is not None:
            items.append((drug, entry["qty"]))

    sale = await create_sale(session, rep=rep, pharmacy=pharmacy, doctor=doctor, items=items)
    await session.commit()
    await state.clear()

    detail = "\n".join(
        f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')} × {_num(c['rate'])} = {_num(Decimal(c['rate']) * c['qty'])}"
        for i, c in enumerate(cart, 1)
    )
    await callback.message.answer(
        t(
            lang,
            "sale_done",
            doctor=doctor.full_name if doctor else "-",
            bonus=_num(sale.total_bonus),
            detail=detail,
        )
    )
    await callback.answer()
    await answer_media(
        callback.message, screen="menu", text=t(lang, "menu_text"), lang=lang,
        reply_markup=main_menu(rep.role, lang), sticker=False,
    )
