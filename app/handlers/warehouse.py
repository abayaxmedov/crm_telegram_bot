from __future__ import annotations

"""Складга заявка — faqat REGIONAL_MANAGER va MANAGER (medvakil).

Bo'lim tanlangach ikki usul chiqadi: (1) ИНН orqali topish, (2) aptekalar ro'yxati.
Aptekalar faqat sotuvchining regioni bo'yicha ko'rinadi (soxta callback'ларга qarshi
tanlangan apteka region + APPROVED bo'yicha qayta tekshiriladi)."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Pharmacy, Role, User
from app.db.repositories import (
    create_warehouse_request,
    drug_price_for,
    get_contract,
    get_drug,
    get_pharmacy,
    list_contracts_for_pharmacy,
    request_contract,
    search_pharmacies_visible,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import (
    contracts_inline,
    inline_id_grid,
    main_menu,
    wh_cart_keyboard,
    wh_method_keyboard,
    wh_payment_keyboard,
)
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import pharmacy_visible_to

router = Router(name="warehouse")

WAREHOUSE_ROLES = {Role.MANAGER, Role.REGIONAL_MANAGER}


class WarehouseFlow(StatesGroup):
    inn = State()
    qty = State()


async def _require_wh_user(callback: CallbackQuery, session: AsyncSession, lang: str) -> User | None:
    """Callback bosqichlari uchun rol tekshiruvi (soxta callback'larga qarshi)."""
    user = await require_callback_user(callback, session)
    if user is None:
        return None
    if user.role not in WAREHOUSE_ROLES:
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return None
    return user


def _pharmacy_in_scope(user: User, pharmacy: Pharmacy | None) -> bool:
    """Tanlangan apteka APPROVED va sotuvchi ko'lamида bo'lishi shart
    (medvakil => faqat o'zi yaratgan; regional => o'z regioni)."""
    if pharmacy is None or pharmacy.approval_status != ApprovalStatus.APPROVED:
        return False
    return pharmacy_visible_to(user, pharmacy)


def _ph_label(pharmacy: Pharmacy) -> str:
    if pharmacy.filial:
        return f"{pharmacy.name} (Филиал: {pharmacy.filial})"
    return pharmacy.name


def _contract_label(contract, lang: str) -> str:
    date = contract.signed_date or t(lang, "contract_no_date")
    return f"Договор №{contract.number} ({date})"


def _num(value) -> str:
    d = Decimal(str(value or 0))
    return f"{d:,.2f}"


def _cart_line(lang: str, index: int, entry: dict) -> str:
    price = Decimal(str(entry.get("price") or 0))
    qty = int(entry["qty"])
    return f"{index}. {entry['name']} — {qty} {t(lang, 'pcs')}. × {_num(price)} = {_num(price * qty)}"


def _cart_total(cart: list[dict]) -> Decimal:
    return sum(
        (Decimal(str(c.get("price") or 0)) * int(c["qty"]) for c in cart), Decimal("0")
    )


def _cart_text(lang: str, cart: list[dict]) -> str:
    lines = [_cart_line(lang, i, c) for i, c in enumerate(cart, 1)]
    return t(lang, "wh_cart_title") + "\n" + "\n".join(lines)


def _pharmacy_list_text(lang: str, pharmacies: list[Pharmacy]) -> str:
    lines = [f"#{p.id} | {safe(_ph_label(p))} | ИНН {safe(p.inn)}" for p in pharmacies]
    return t(lang, "wh_list_header") + "\n\n" + "\n".join(lines)


async def _send_drug_choice(message: Message, session: AsyncSession, user: User, lang: str, state: FSMContext) -> None:
    await show_list(message, session, user, lang, state, "wh_drug")


# ==================== Kirish: usul tanlash ====================


@router.message(F.text.in_(variants("btn_warehouse")), RoleFilter(Role.MANAGER, Role.REGIONAL_MANAGER))
async def wh_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await require_user(message, session) is None:
        return
    await state.clear()
    await message.answer(t(lang, "wh_choose_method"), reply_markup=wh_method_keyboard(lang))


@router.callback_query(F.data == "wh_method:inn")
async def wh_method_inn(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await _require_wh_user(callback, session, lang) is None:
        return
    await state.set_state(WarehouseFlow.inn)
    await callback.message.answer(t(lang, "wh_enter_inn"))
    await callback.answer()


@router.callback_query(F.data == "wh_method:list")
async def wh_method_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await _require_wh_user(callback, session, lang)
    if user is None:
        return
    await state.clear()
    await show_list(callback.message, session, user, lang, state, "wh_ph")
    await callback.answer()


@router.message(WarehouseFlow.inn)
async def wh_search_inn(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None or user.role not in WAREHOUSE_ROLES:
        await state.clear()
        return
    query = (message.text or "").strip()
    if not query:
        await message.answer(t(lang, "wh_enter_inn"))
        return
    pharmacies = await search_pharmacies_visible(session, user, query)
    if not pharmacies:
        await message.answer(t(lang, "wh_not_found"))
        return
    await state.clear()
    await message.answer(
        _pharmacy_list_text(lang, pharmacies),
        reply_markup=inline_id_grid([p.id for p in pharmacies], "wh_ph"),
    )


# ==================== Apteka tanlangach: shartnoma -> savat ====================


@router.callback_query(F.data.startswith("wh_ph:"))
async def wh_pick_pharmacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await _require_wh_user(callback, session, lang)
    if user is None:
        return
    pharmacy = await get_pharmacy(session, int(callback.data.split(":", 1)[1]))
    if not _pharmacy_in_scope(user, pharmacy):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await state.update_data(pharmacy_id=pharmacy.id, cart=[])
    contracts = await list_contracts_for_pharmacy(session, pharmacy.id)
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
    if not _pharmacy_in_scope(rep, pharmacy):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
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
    user = await _require_wh_user(callback, session, lang)
    if user is None:
        return
    data = await state.get_data()
    if not data.get("pharmacy_id"):
        await callback.answer(t(lang, "flow_expired"), show_alert=True)
        return
    await state.update_data(contract_id=int(callback.data.split(":", 1)[1]), cart=[])
    # Preparat narxi apteka boshlang'ich to'lov shartiga bog'liq — avval shuni so'raymiz.
    await callback.message.answer(t(lang, "wh_choose_payment"), reply_markup=wh_payment_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data.startswith("wh_pay:"))
async def wh_pick_payment(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await _require_wh_user(callback, session, lang)
    if user is None:
        return
    data = await state.get_data()
    if not data.get("pharmacy_id"):
        await callback.answer(t(lang, "flow_expired"), show_alert=True)
        return
    raw = callback.data.split(":", 1)[1]
    if raw not in {"50", "100"}:
        await callback.answer()
        return
    # Savat narx snapshot'lari shu foizga bog'liq — foiz o'zgarsa savat tozalanadi.
    await state.update_data(payment_percent=int(raw), cart=[])
    await callback.message.answer(t(lang, "wh_payment_set", percent=int(raw)))
    await _send_drug_choice(callback.message, session, user, lang, state)
    await callback.answer()


@router.callback_query(F.data.startswith("wh_drug:"))
async def wh_pick_drug(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await _require_wh_user(callback, session, lang) is None:
        return
    data = await state.get_data()
    if not data.get("pharmacy_id") or not data.get("payment_percent"):
        await callback.answer(t(lang, "flow_expired"), show_alert=True)
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
    percent = int(data.get("payment_percent") or 100)
    cart.append(
        {
            "drug_id": drug.id,
            "name": drug.name,
            "qty": int(raw),
            "price": str(drug_price_for(drug, percent)),
        }
    )
    await state.update_data(cart=cart)
    await state.set_state(None)
    await message.answer(_cart_text(lang, cart), reply_markup=wh_cart_keyboard(lang))


@router.callback_query(F.data == "wh_cart:add")
async def wh_cart_add(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await _require_wh_user(callback, session, lang)
    if user is None:
        return
    await _send_drug_choice(callback.message, session, user, lang, state)
    await callback.answer()


@router.callback_query(F.data == "wh_cart:finish")
async def wh_cart_finish(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_wh_user(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    # Double-tap himoyasi: state'ni yaratishdan oldin tozalaymiz.
    await state.clear()
    cart = data.get("cart", [])
    if not cart or not data.get("pharmacy_id") or not data.get("payment_percent"):
        await callback.answer(t(lang, "cart_empty"), show_alert=True)
        return
    percent = int(data["payment_percent"])

    pharmacy = await get_pharmacy(session, data["pharmacy_id"])
    if not _pharmacy_in_scope(rep, pharmacy):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    contract = await get_contract(session, data["contract_id"]) if data.get("contract_id") else None

    items = []
    for entry in cart:
        drug = await get_drug(session, entry["drug_id"])
        if drug is not None:
            items.append((drug, entry["qty"]))

    request = await create_warehouse_request(
        session, rep=rep, pharmacy=pharmacy, contract=contract, items=items, payment_percent=percent
    )
    await session.commit()

    detail = "\n".join(_cart_line(lang, i, c) for i, c in enumerate(cart, 1))
    await callback.message.answer(
        t(
            lang,
            "wh_done",
            id=request.id,
            pharmacy=_ph_label(pharmacy) if pharmacy else "-",
            contract=_contract_label(contract, lang) if contract else "-",
            percent=percent,
            detail=detail,
            total=_num(_cart_total(cart)),
        )
    )
    await callback.answer()
    await answer_media(
        callback.message, screen="menu", text=t(lang, "menu_text"), lang=lang,
        reply_markup=main_menu(rep.role, lang), sticker=False,
    )
