from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Pharmacy, Role
from app.db.repositories import (
    create_warehouse_request,
    get_contract,
    get_drug,
    get_pharmacy,
    list_active_drugs,
    list_contracts_for_pharmacy,
    request_contract,
    search_pharmacies,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user
from app.i18n import t, variants
from app.keyboards.reply import contracts_inline, entities_inline, main_menu, wh_cart_keyboard
from app.services.media import answer_media


WAREHOUSE_ROLES = {Role.MANAGER, Role.OWNER}


async def _require_wh_user(callback, session, lang):
    """Callback bosqichlari uchun rol tekshiruvi (soxta callback'larga qarshi)."""
    user = await require_callback_user(callback, session)
    if user is None:
        return None
    if user.role not in WAREHOUSE_ROLES:
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return None
    return user

router = Router(name="warehouse")


class WarehouseFlow(StatesGroup):
    search = State()
    qty = State()


def _ph_label(pharmacy: Pharmacy) -> str:
    if pharmacy.filial:
        return f"{pharmacy.name} (Филиал: {pharmacy.filial})"
    return pharmacy.name


def _contract_label(contract, lang: str) -> str:
    date = contract.signed_date or t(lang, "contract_no_date")
    return f"Договор №{contract.number} ({date})"


def _cart_text(lang: str, cart: list[dict]) -> str:
    lines = [f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')}." for i, c in enumerate(cart, 1)]
    return t(lang, "wh_cart_title") + "\n" + "\n".join(lines)


async def _send_drug_choice(message: Message, session: AsyncSession, lang: str) -> None:
    drugs = await list_active_drugs(session)
    if not drugs:
        await message.answer(t(lang, "sales_no_drugs"))
        return
    items = [(d.id, d.name) for d in drugs]
    await message.answer(t(lang, "wh_choose_drug"), reply_markup=entities_inline(items, "wh_drug"))


@router.message(F.text.in_(variants("btn_warehouse")), RoleFilter(Role.MANAGER))
async def wh_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await require_user(message, session) is None:
        return
    await state.clear()
    await state.set_state(WarehouseFlow.search)
    await message.answer(t(lang, "wh_search_pharmacy"))


@router.message(WarehouseFlow.search)
async def wh_search(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None or user.role not in WAREHOUSE_ROLES:
        await state.clear()
        return
    query = (message.text or "").strip()
    pharmacies = await search_pharmacies(session, query)
    if not pharmacies:
        await message.answer(t(lang, "wh_not_found"))
        return
    await state.set_state(None)
    await message.answer(
        t(lang, "sales_choose_pharmacy"),
        reply_markup=entities_inline([(p.id, _ph_label(p)) for p in pharmacies], "wh_ph"),
    )


@router.callback_query(F.data.startswith("wh_ph:"))
async def wh_pick_pharmacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await _require_wh_user(callback, session, lang) is None:
        return
    pharmacy_id = int(callback.data.split(":", 1)[1])
    await state.update_data(pharmacy_id=pharmacy_id, cart=[])
    contracts = await list_contracts_for_pharmacy(session, pharmacy_id)
    await callback.message.answer(
        t(lang, "wh_choose_contract"),
        reply_markup=contracts_inline([(c.id, _contract_label(c, lang)) for c in contracts], lang),
    )
    await callback.answer()


@router.callback_query(F.data == "wh_contract:new")
async def wh_request_contract(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_wh_user(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    pharmacy = await get_pharmacy(session, data.get("pharmacy_id")) if data.get("pharmacy_id") else None
    if pharmacy is not None:
        await request_contract(session, pharmacy=pharmacy, rep=rep)
        await session.commit()
    await state.clear()
    await callback.message.answer(t(lang, "wh_contract_requested"))
    await callback.answer()
    await answer_media(
        callback.message, screen="menu", text=t(lang, "menu_text"), lang=lang,
        reply_markup=main_menu(rep.role, lang), sticker=False,
    )


@router.callback_query(F.data.startswith("wh_contract:"))
async def wh_pick_contract(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await _require_wh_user(callback, session, lang) is None:
        return
    await state.update_data(contract_id=int(callback.data.split(":", 1)[1]), cart=[])
    await _send_drug_choice(callback.message, session, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("wh_drug:"))
async def wh_pick_drug(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await _require_wh_user(callback, session, lang) is None:
        return
    drug = await get_drug(session, int(callback.data.split(":", 1)[1]))
    if drug is None:
        await callback.answer()
        return
    await state.update_data(current_drug_id=drug.id)
    await state.set_state(WarehouseFlow.qty)
    await callback.message.answer(t(lang, "wh_enter_qty", name=drug.name))
    await callback.answer()


@router.message(WarehouseFlow.qty)
async def wh_qty(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None or user.role not in WAREHOUSE_ROLES:
        await state.clear()
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(t(lang, "qty_invalid"))
        return
    data = await state.get_data()
    drug = await get_drug(session, data.get("current_drug_id"))
    if drug is None:
        await state.set_state(None)
        return
    cart = data.get("cart", [])
    cart.append({"drug_id": drug.id, "name": drug.name, "qty": int(raw)})
    await state.update_data(cart=cart)
    await state.set_state(None)
    await message.answer(_cart_text(lang, cart), reply_markup=wh_cart_keyboard(lang))


@router.callback_query(F.data == "wh_cart:add")
async def wh_cart_add(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    if await _require_wh_user(callback, session, lang) is None:
        return
    await _send_drug_choice(callback.message, session, lang)
    await callback.answer()


@router.callback_query(F.data == "wh_cart:finish")
async def wh_cart_finish(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_wh_user(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await callback.answer(t(lang, "cart_empty"), show_alert=True)
        return

    pharmacy = await get_pharmacy(session, data["pharmacy_id"]) if data.get("pharmacy_id") else None
    contract = await get_contract(session, data["contract_id"]) if data.get("contract_id") else None

    items = []
    for entry in cart:
        drug = await get_drug(session, entry["drug_id"])
        if drug is not None:
            items.append((drug, entry["qty"]))

    request = await create_warehouse_request(session, rep=rep, pharmacy=pharmacy, contract=contract, items=items)
    await session.commit()
    await state.clear()

    detail = "\n".join(f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')}." for i, c in enumerate(cart, 1))
    await callback.message.answer(
        t(
            lang,
            "wh_done",
            id=request.id,
            pharmacy=_ph_label(pharmacy) if pharmacy else "-",
            contract=_contract_label(contract, lang) if contract else "-",
            detail=detail,
        )
    )
    await callback.answer()
    await answer_media(
        callback.message, screen="menu", text=t(lang, "menu_text"), lang=lang,
        reply_markup=main_menu(rep.role, lang), sticker=False,
    )
