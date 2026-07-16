from __future__ import annotations

"""Оптомдан приход — medvakil kiritadi, TOP menejer REAL-TIME tasdiqlaydi.

Oqim: qaysi APTEKA prixod oldi -> qaysi ОПТОМдан -> qaysi preparatdan qancha
(savat) -> yakunlash. Yakunlangач barcha faol TOP menejerlarga karta + ✅/❌
tugmalari yuboriladi. Apteka qoldig'i FAQAT tasdiqlangandan keyin oshadi.

Sklad zayavkasidan farqi: bu yerda dori kompaniya omboridan emas, tashqi
optomdan keladi — shuning uchun narx/to'lov sharti so'ralmaydi."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Pharmacy, Role, User
from app.db.repositories import (
    create_wholesale_income,
    get_drug,
    get_pharmacy,
    get_wholesale_income,
    get_wholesaler,
    list_pending_wholesale_incomes,
    list_wholesalers,
    set_wholesale_income_status,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import normalize, t, variants
from app.keyboards.reply import main_menu, wi_cart_keyboard
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.wholesale_notify import notify_top_new_income, wi_approve_keyboard, wi_card
from app.services.security import (
    can_add_wholesale_income,
    can_approve_wholesale_income,
    pharmacy_visible_to,
)

router = Router(name="wholesale_income")


class WholesaleIncomeFlow(StatesGroup):
    qty = State()


async def _require_rep(callback: CallbackQuery, session: AsyncSession, lang: str) -> User | None:
    """Callback bosqichlarида rol tekshiruvi (soxta callback'larga qarshi)."""
    user = await require_callback_user(callback, session)
    if user is None:
        return None
    if not can_add_wholesale_income(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return None
    return user


def _ph_label(pharmacy: Pharmacy) -> str:
    if pharmacy.filial:
        return f"{pharmacy.name} (Филиал: {pharmacy.filial})"
    return pharmacy.name


def _cart_text(lang: str, cart: list[dict]) -> str:
    lines = [f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')}." for i, c in enumerate(cart, 1)]
    return t(lang, "wi_cart_title") + "\n" + "\n".join(lines)


# ==================== Medvakil: prixod kiritish ====================


@router.message(F.text.in_(variants("btn_wholesale_income")), RoleFilter(Role.MANAGER, Role.OWNER))
async def wi_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await state.clear()
    await show_list(message, session, user, lang, state, "wi_ph")


@router.callback_query(F.data.startswith("wi_ph:"))
async def wi_pick_pharmacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_rep(callback, session, lang)
    if rep is None:
        return
    pharmacy = await get_pharmacy(session, int(callback.data.split(":", 1)[1]))
    if (
        pharmacy is None
        or pharmacy.approval_status != ApprovalStatus.APPROVED
        or not pharmacy_visible_to(rep, pharmacy)
    ):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    if not await list_wholesalers(session):
        await callback.answer(t(lang, "wi_no_wholesalers"), show_alert=True)
        return
    await state.update_data(pharmacy_id=pharmacy.id, wholesaler_id=None, cart=[])
    await show_list(callback.message, session, rep, lang, state, "wi_optom")
    await callback.answer()


@router.callback_query(F.data.startswith("wi_optom:"))
async def wi_pick_wholesaler(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_rep(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    if not data.get("pharmacy_id"):
        await callback.answer(t(lang, "flow_expired"), show_alert=True)
        return
    wholesaler = await get_wholesaler(session, int(callback.data.split(":", 1)[1]))
    if wholesaler is None or not wholesaler.is_active:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await state.update_data(wholesaler_id=wholesaler.id, cart=[])
    await show_list(callback.message, session, rep, lang, state, "wi_drug")
    await callback.answer()


@router.callback_query(F.data.startswith("wi_drug:"))
async def wi_pick_drug(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_rep(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    if not data.get("pharmacy_id") or not data.get("wholesaler_id"):
        await callback.answer(t(lang, "flow_expired"), show_alert=True)
        return
    drug = await get_drug(session, int(callback.data.split(":", 1)[1]))
    if drug is None:
        await callback.answer()
        return
    await state.update_data(current_drug_id=drug.id)
    await state.set_state(WholesaleIncomeFlow.qty)
    await callback.message.answer(t(lang, "wi_enter_qty", name=safe(drug.name)))
    await callback.answer()


@router.message(WholesaleIncomeFlow.qty)
async def wi_qty(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None or not can_add_wholesale_income(rep.role):
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
    await message.answer(_cart_text(lang, cart), reply_markup=wi_cart_keyboard(lang))


@router.callback_query(F.data == "wi_cart:add")
async def wi_cart_add(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_rep(callback, session, lang)
    if rep is None:
        return
    await show_list(callback.message, session, rep, lang, state, "wi_drug")
    await callback.answer()


@router.callback_query(F.data == "wi_cart:finish")
async def wi_cart_finish(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_rep(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    # Double-tap himoyasi: state yaratishdan OLDIN tozalanadi.
    await state.clear()
    cart = data.get("cart", [])
    if not cart or not data.get("pharmacy_id") or not data.get("wholesaler_id"):
        await callback.answer(t(lang, "cart_empty"), show_alert=True)
        return

    pharmacy = await get_pharmacy(session, data["pharmacy_id"])
    if (
        pharmacy is None
        or pharmacy.approval_status != ApprovalStatus.APPROVED
        or not pharmacy_visible_to(rep, pharmacy)
    ):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    wholesaler = await get_wholesaler(session, data["wholesaler_id"])
    if wholesaler is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return

    items = []
    for entry in cart:
        drug = await get_drug(session, entry["drug_id"])
        if drug is not None:
            items.append((drug, entry["qty"]))

    income = await create_wholesale_income(
        session, rep=rep, pharmacy=pharmacy, wholesaler=wholesaler, items=items
    )
    await session.commit()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    detail = "\n".join(f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')}." for i, c in enumerate(cart, 1))
    await callback.message.answer(
        t(
            lang,
            "wi_done",
            id=income.id,
            pharmacy=safe(_ph_label(pharmacy)),
            wholesaler=safe(wholesaler.name),
            detail=detail,
        )
    )
    # TOP menejerlarga REAL-TIME so'rov (huddi dorixona tasdig'i kabi).
    await notify_top_new_income(callback.bot, session, income.id)
    await callback.answer()
    await answer_media(
        callback.message, screen="menu", text=t(lang, "menu_text"), lang=lang,
        reply_markup=main_menu(rep.role, lang), sticker=False,
    )


# ==================== TOP menejer: tasdiqlash ====================


@router.message(F.text.in_(variants("btn_wi_approve")), RoleFilter(Role.TOP_MANAGER, Role.OWNER))
async def wi_approve_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    incomes = await list_pending_wholesale_incomes(session)
    if not incomes:
        await message.answer(t(lang, "wi_approve_empty"))
        return
    await message.answer(t(lang, "wi_approve_header"))
    for income in incomes:
        await message.answer(wi_card(lang, income), reply_markup=wi_approve_keyboard(lang, income.id))


async def _decide(callback: CallbackQuery, session: AsyncSession, lang: str, status: ApprovalStatus) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_approve_wholesale_income(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    income = await get_wholesale_income(session, int(callback.data.split(":", 1)[1]))
    if income is None or income.status != ApprovalStatus.PENDING:
        await callback.answer(t(lang, "wi_not_found"), show_alert=True)
        return
    await set_wholesale_income_status(session, income=income, status=status, actor=user)
    await session.commit()

    result_key = "wi_approved" if status == ApprovalStatus.APPROVED else "wi_rejected"
    await callback.message.edit_text(wi_card(lang, income) + "\n\n" + t(lang, result_key, id=income.id))

    # Kirituvchi medvakilga natija haqida xabar.
    if income.rep is not None and income.rep.telegram_id:
        rep_lang = normalize(income.rep.language)
        rep_key = "wi_approved_rep" if status == ApprovalStatus.APPROVED else "wi_rejected_rep"
        try:
            await callback.bot.send_message(
                income.rep.telegram_id,
                t(
                    rep_lang,
                    rep_key,
                    id=income.id,
                    pharmacy=safe(_ph_label(income.pharmacy)) if income.pharmacy else "-",
                ),
            )
        except Exception:  # bot bloklangan / chat topilmadi
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("wi_ok:"))
async def wi_ok(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    await _decide(callback, session, lang, ApprovalStatus.APPROVED)


@router.callback_query(F.data.startswith("wi_reject:"))
async def wi_reject(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    await _decide(callback, session, lang, ApprovalStatus.REJECTED)
