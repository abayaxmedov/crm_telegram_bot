from __future__ import annotations

"""Sotuv kiritish — medvakil VA regional menejer.

Sotuvda dorixona va doktor tanlanadi; doktor balansidan dorining aksiya balli
ayiriladi (manfiyga o'tishi mumkin). Sotuvda doktorga xabar YUBORILMAYDI —
doktor faqat ball tushishi (o'tkazma) tasdig'ini oladi."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role, User
from app.db.repositories import (
    create_sale,
    get_ball_balance,
    get_doctor,
    get_doctor_with_user,
    get_drug,
    get_pharmacy,
    get_pharmacy_stock_qty,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user
from app.i18n import normalize, t, variants
from app.keyboards.reply import main_menu, sale_cart_keyboard
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.notify import send_to_doctor
from app.services.security import can_record_sales, doctor_visible_to, pharmacy_visible_to

router = Router(name="sales")

SELLER_ROLES = (Role.MANAGER, Role.REGIONAL_MANAGER)


class SalesFlow(StatesGroup):
    qty = State()


async def _require_seller(callback: CallbackQuery, session: AsyncSession, lang: str) -> User | None:
    """Callback bosqichlari uchun ham rol tekshiruvi (soxta callback'larga qarshi)."""
    user = await require_callback_user(callback, session)
    if user is None:
        return None
    if not can_record_sales(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return None
    return user


def _entity_in_scope(user: User, entity) -> bool:
    """Tanlangan doktor APPROVED va sotuvchi ko'lamида (o'zi yaratgan) bo'lishi shart."""
    if entity is None or entity.approval_status != ApprovalStatus.APPROVED:
        return False
    return doctor_visible_to(user, entity)


def _num(value) -> str:
    d = Decimal(str(value))
    return str(int(d)) if d == d.to_integral_value() else f"{d:.2f}"


def _cart_text(lang: str, cart: list[dict]) -> str:
    lines = [
        f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')}. (💠 {int(c['ball']) * int(c['qty'])})"
        for i, c in enumerate(cart, 1)
    ]
    return t(lang, "cart_title") + "\n" + "\n".join(lines)


async def _send_drug_choice(message: Message, session: AsyncSession, user: User, lang: str, state: FSMContext) -> None:
    data = await state.get_data()
    # Faqat shu dorixonaда qoldig'i bor dorilar (остаток bilan) ko'rsatiladi.
    await show_list(message, session, user, lang, state, "sale_drug", ctx={"pharmacy_id": data.get("pharmacy_id")})


@router.message(F.text.in_(variants("btn_sales")), RoleFilter(*SELLER_ROLES))
async def sales_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    await state.clear()
    await show_list(message, session, rep, lang, state, "sale_ph")


@router.callback_query(F.data.startswith("sale_ph:"))
async def sale_pick_pharmacy(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_seller(callback, session, lang)
    if rep is None:
        return
    pharmacy = await get_pharmacy(session, int(callback.data.split(":", 1)[1]))
    # Soxta callback'ga qarshi: dorixona APPROVED va sotuvchi ko'lamида bo'lishi shart
    # (medvakil => faqat o'zi yaratgan; regional => o'z regioni).
    if pharmacy is None or pharmacy.approval_status != ApprovalStatus.APPROVED or not pharmacy_visible_to(rep, pharmacy):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await state.update_data(pharmacy_id=pharmacy.id, doctor_id=None, cart=[])
    await show_list(callback.message, session, rep, lang, state, "sale_doc")
    await callback.answer()


@router.callback_query(F.data.startswith("sale_doc:"))
async def sale_pick_doctor(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_seller(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    if not data.get("pharmacy_id"):
        # Eski (stale) tugma — oqim boshidan boshlanishi kerak.
        await callback.answer(t(lang, "flow_expired"), show_alert=True)
        return
    doctor = await get_doctor(session, int(callback.data.split(":", 1)[1]))
    if not _entity_in_scope(rep, doctor):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await state.update_data(doctor_id=doctor.id)
    await _send_drug_choice(callback.message, session, rep, lang, state)
    await callback.answer()


@router.callback_query(F.data.startswith("sale_drug:"))
async def sale_pick_drug(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_seller(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    if not data.get("pharmacy_id") or not data.get("doctor_id"):
        await callback.answer(t(lang, "flow_expired"), show_alert=True)
        return
    drug = await get_drug(session, int(callback.data.split(":", 1)[1]))
    if drug is None:
        await callback.answer()
        return
    await state.update_data(current_drug_id=drug.id)
    await state.set_state(SalesFlow.qty)
    remain = await get_pharmacy_stock_qty(session, data["pharmacy_id"], drug.id)
    await callback.message.answer(t(lang, "sales_drug_info", name=drug.name, stock=remain))
    await callback.answer()


@router.message(SalesFlow.qty)
async def sale_qty(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None or not can_record_sales(rep.role):
        await state.clear()
        return
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
    cart = data.get("cart", [])
    # Dorixona qoldig'i (остаток) bo'yicha tekshiramiz (savatdagi shu dori qatorlari ham hisobga olinadi).
    available = await get_pharmacy_stock_qty(session, data["pharmacy_id"], drug.id)
    already = sum(int(c["qty"]) for c in cart if c["drug_id"] == drug.id)
    if qty + already > available:
        await message.answer(t(lang, "qty_over_stock", stock=max(0, available - already)))
        return

    cart.append(
        {
            "drug_id": drug.id,
            "name": drug.name,
            "qty": qty,
            "price": str(drug.price_100 or drug.price or 0),  # sotuv 100% narxда
            "ball": int(drug.ball or 0),
        }
    )
    await state.update_data(cart=cart)
    await state.set_state(None)
    await message.answer(_cart_text(lang, cart), reply_markup=sale_cart_keyboard(lang))


@router.callback_query(F.data == "sale_cart:add")
async def sale_cart_add(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_seller(callback, session, lang)
    if rep is None:
        return
    await _send_drug_choice(callback.message, session, rep, lang, state)
    await callback.answer()


@router.callback_query(F.data == "sale_cart:finish")
async def sale_cart_finish(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await _require_seller(callback, session, lang)
    if rep is None:
        return
    data = await state.get_data()
    # Double-tap himoyasi: state'ni sotuv yaratishdan OLDIN tozalaymiz — ikkinchi
    # bosish bo'sh savatni ko'rib hech narsa yozmaydi.
    await state.clear()
    cart = data.get("cart", [])
    if not cart or not data.get("pharmacy_id") or not data.get("doctor_id"):
        await callback.answer(t(lang, "cart_empty"), show_alert=True)
        return

    pharmacy = await get_pharmacy(session, data["pharmacy_id"])
    doctor = await get_doctor(session, data["doctor_id"])
    if not _entity_in_scope(rep, pharmacy) or not _entity_in_scope(rep, doctor):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return

    items = []
    for entry in cart:
        drug = await get_drug(session, entry["drug_id"])
        if drug is not None:
            items.append((drug, entry["qty"]))

    sale = await create_sale(session, rep=rep, pharmacy=pharmacy, doctor=doctor, items=items)
    await session.commit()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    detail = "\n".join(
        f"{i}. {c['name']} — {c['qty']} {t(lang, 'pcs')} × 💠{c['ball']} = 💠{int(c['ball']) * int(c['qty'])}"
        for i, c in enumerate(cart, 1)
    )
    # Atomik ayirishdan keyin balансни bazadan o'qiymiz.
    doctor_balance = await get_ball_balance(session, doctor_id=doctor.id) if doctor else 0
    await callback.message.answer(
        t(
            lang,
            "sale_done_ball",
            doctor=doctor.full_name if doctor else "-",
            price=_num(sale.total_price),
            ball=sale.total_ball,
            balance=doctor_balance,
            detail=detail,
        )
    )

    # Doktorga ball AYIRILGANI haqida xabar (botga ulangan bo'lsa) — 6 soatda avto-o'chadi.
    if doctor is not None and sale.total_ball > 0:
        doctor_linked = await get_doctor_with_user(session, doctor.id)
        if doctor_linked is not None and doctor_linked.bot_user is not None:
            doc_lang = normalize(doctor_linked.bot_user.language)
            sent = await send_to_doctor(
                callback.bot,
                session,
                doctor_linked,
                t(doc_lang, "ball_deducted_doctor", amount=sale.total_ball, balance=doctor_balance),
            )
            if sent:
                await session.commit()

    await callback.answer()
    await answer_media(
        callback.message, screen="menu", text=t(lang, "menu_text"), lang=lang,
        reply_markup=main_menu(rep.role, lang), sticker=False,
    )
