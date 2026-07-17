from __future__ import annotations

"""🎁 Совға балл — medvakil/regional menejer DOKTORGA ball sovg'a qiladi.

Oqim: doktor tanlash (faqat botga ulanganlar) -> miqdor -> TOP menejerga REAL-TIME
tasdiq so'rovi. TOP tasdiqlagandagina ball yuboruvchi balansidan ATOMIK ayirilib
doktorga o'tadi; doktorga xabar boradi va 6 soatda o'chadi.

«💠 Балл баланси» dagi o'tkazmadan farqi: u yerda tasdiqni QABUL QILUVCHI beradi,
bu yerda esa TOP menejer. Ball manbai ikkalasida ham bir xil — yuboruvchi balansi,
shuning uchun pending sovg'a ham `available_ball` da band hisoblanadi."""

import logging

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BallTxKind, BallTxStatus, Role, User
from app.db.repositories import (
    accept_ball_transfer,
    available_ball,
    create_ball_gift,
    finish_ball_transfer,
    get_ball_balance,
    get_ball_transaction,
    get_doctor_with_user,
    list_pending_gifts,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import normalize, role_label, t, variants
from app.keyboards.reply import gift_approve_keyboard
from app.services.listing import show_list
from app.services.notify import send_to_doctor
from app.services.security import can_approve_gift, can_send_gift, doctor_visible_to

logger = logging.getLogger(__name__)

router = Router(name="gift")


class GiftFlow(StatesGroup):
    amount = State()


def _gift_card(lang: str, tx) -> str:
    """Sovg'a kartasi — from_user/to_doctor EAGER-LOAD bo'lishi shart."""
    sender = tx.from_user
    return t(
        lang,
        "gift_card",
        id=tx.id,
        sender=safe(sender.full_name if sender else None),
        role=role_label(lang, sender.role) if sender else "-",
        doctor=safe(tx.to_doctor.full_name if tx.to_doctor else None),
        amount=int(tx.amount),
        date=str(tx.created_at)[:16] if tx.created_at else "-",
    )


async def _active_tops(session: AsyncSession) -> list[User]:
    return list(
        (
            await session.execute(
                select(User).where(
                    User.role == Role.TOP_MANAGER, User.is_active.is_(True), User.telegram_id.is_not(None)
                )
            )
        ).scalars()
    )


# ==================== Medvakil/regional: sovg'a yuborish ====================


@router.message(F.text.in_(variants("btn_gift")), RoleFilter(Role.MANAGER, Role.REGIONAL_MANAGER, Role.OWNER))
async def gift_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_send_gift(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await state.clear()
    available = await available_ball(session, user)
    await show_list(
        message, session, user, lang, state, "gift_doc", ctx={"available": available}
    )


@router.callback_query(F.data.startswith("gift_doc:"))
async def gift_pick_doctor(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    sender = await require_callback_user(callback, session)
    if sender is None:
        return
    if not can_send_gift(sender.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    doctor = await get_doctor_with_user(session, int(callback.data.split(":", 1)[1]))
    # Soxta callback'ga qarshi: doktor ko'lamда VA botga ulangan bo'lishi shart.
    if (
        doctor is None
        or not doctor_visible_to(sender, doctor)
        or doctor.bot_user is None
        or doctor.bot_user.telegram_id is None
    ):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await state.update_data(doctor_id=doctor.id)
    await state.set_state(GiftFlow.amount)
    available = await available_ball(session, sender)
    await callback.message.answer(
        t(lang, "gift_enter_amount", doctor=escape(doctor.full_name), available=available)
    )
    await callback.answer()


@router.message(GiftFlow.amount)
async def gift_amount(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    sender = await require_user(message, session)
    if sender is None or not can_send_gift(sender.role):
        await state.clear()
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(t(lang, "ball_amount_invalid"))
        return
    amount = int(raw)

    # Balans tekshiruvi: pending sovg'a/o'tkazmalar ham band hisoblanadi.
    available = await available_ball(session, sender)
    if amount > available:
        await message.answer(t(lang, "ball_insufficient", available=available))
        return

    data = await state.get_data()
    doctor = await get_doctor_with_user(session, data.get("doctor_id"))
    if doctor is None or not doctor_visible_to(sender, doctor) or doctor.bot_user is None:
        await state.clear()
        await message.answer(t(lang, "gift_no_doctors"))
        return

    tops = await _active_tops(session)
    if not tops:
        # Tasdiqlovchi yo'q — sovg'a yaratmaymiz (balans behuda band bo'lmasin).
        await state.clear()
        await message.answer(t(lang, "gift_no_top"))
        return

    created = await create_ball_gift(session, sender=sender, doctor=doctor, amount=amount)
    # Avval commit — TOP tugmani bosganда tx bazada bo'lishi shart.
    await session.commit()
    await state.clear()
    # Kartani qurish uchun relationship'lar kerak — EAGER-LOAD bilan qayta o'qiymiz
    # (yangi yaratilgan obyektda ular lazy bo'lib, async'da MissingGreenlet beradi).
    tx = await get_ball_transaction(session, created.id)
    if tx is None:
        await message.answer(t(lang, "gift_no_top"))
        return

    delivered = 0
    for top in tops:
        top_lang = normalize(top.language)
        try:
            await message.bot.send_message(
                top.telegram_id,
                t(top_lang, "new_gift_for_approve", card=_gift_card(top_lang, tx)),
                reply_markup=gift_approve_keyboard(top_lang, tx.id),
            )
            delivered += 1
        except Exception as exc:  # bot bloklangan / chat topilmadi
            logger.warning("TOP gift notify failed (top=%s): %s", top.id, exc)
            continue

    if not delivered:
        # Hech bir TOP'ga yetib bormadi — pending qoldirmaymiz (balans band bo'lardi).
        await finish_ball_transfer(session, tx, sender, BallTxStatus.REJECTED)
        await session.commit()
        await message.answer(t(lang, "gift_no_top"))
        return

    await message.answer(
        t(lang, "gift_sent", amount=amount, doctor=escape(doctor.full_name))
    )


# ==================== TOP menejer: tasdiqlash ====================


@router.message(F.text.in_(variants("btn_gift_approve")), RoleFilter(Role.TOP_MANAGER, Role.OWNER))
async def gift_approve_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    gifts = await list_pending_gifts(session)
    if not gifts:
        await message.answer(t(lang, "gift_approve_empty"))
        return
    await message.answer(t(lang, "gift_approve_header"))
    for tx in gifts:
        await message.answer(_gift_card(lang, tx), reply_markup=gift_approve_keyboard(lang, tx.id))


async def _notify_sender(bot, tx, key: str, **kwargs) -> None:
    sender = tx.from_user
    if sender is None or not sender.telegram_id:
        return
    slang = normalize(sender.language)
    try:
        await bot.send_message(sender.telegram_id, t(slang, key, **kwargs))
    except Exception:  # bot bloklangan
        pass


@router.callback_query(F.data.startswith("gift_ok:"))
async def gift_ok(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    top = await require_callback_user(callback, session)
    if top is None:
        return
    if not can_approve_gift(top.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    tx = await get_ball_transaction(session, int(callback.data.split(":", 1)[1]))
    if tx is None or tx.kind != BallTxKind.GIFT or tx.status != BallTxStatus.PENDING:
        await callback.answer(t(lang, "gift_not_found"), show_alert=True)
        return

    doctor_name = tx.to_doctor.full_name if tx.to_doctor else "-"
    amount = int(tx.amount)
    # Atomik: PENDING->ACCEPTED da'vo + shartli ayirish (parallel TOP'lar poygasida bittasi yutadi).
    result = await accept_ball_transfer(session, tx, top)
    await session.commit()

    if result == "conflict":
        await callback.answer(t(lang, "gift_not_found"), show_alert=True)
        return
    if result == "insufficient":
        # Sovg'a yaratilgandan keyin yuboruvchi balansi tushib ketgan.
        await callback.message.edit_text(
            _gift_card(lang, tx) + "\n\n" + t(lang, "gift_insufficient_now", id=tx.id)
        )
        await _notify_sender(
            callback.bot, tx, "gift_insufficient_sender", amount=amount, doctor=escape(doctor_name)
        )
        await callback.answer()
        return

    await callback.message.edit_text(_gift_card(lang, tx) + "\n\n" + t(lang, "gift_approved", id=tx.id))

    # Doktorga xabar — 6 soatda avto-o'chadi (DOCTOR_MESSAGE_TTL).
    if tx.to_doctor is not None:
        doc_balance = await get_ball_balance(session, doctor_id=tx.to_doctor.id)
        doc_lang = normalize(tx.to_doctor.bot_user.language) if tx.to_doctor.bot_user else lang
        sent = await send_to_doctor(
            callback.bot,
            session,
            tx.to_doctor,
            t(
                doc_lang,
                "gift_doctor_notice",
                sender=escape(tx.from_user.full_name) if tx.from_user else "-",
                amount=amount,
                balance=doc_balance,
            ),
        )
        if sent:
            await session.commit()

    sender_balance = await get_ball_balance(session, user_id=tx.from_user_id)
    await _notify_sender(
        callback.bot, tx, "gift_approved_sender",
        amount=amount, doctor=escape(doctor_name), balance=sender_balance,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gift_rej:"))
async def gift_reject(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    top = await require_callback_user(callback, session)
    if top is None:
        return
    if not can_approve_gift(top.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    tx = await get_ball_transaction(session, int(callback.data.split(":", 1)[1]))
    if tx is None or tx.kind != BallTxKind.GIFT or tx.status != BallTxStatus.PENDING:
        await callback.answer(t(lang, "gift_not_found"), show_alert=True)
        return

    doctor_name = tx.to_doctor.full_name if tx.to_doctor else "-"
    amount = int(tx.amount)
    if not await finish_ball_transfer(session, tx, top, BallTxStatus.REJECTED):
        await callback.answer(t(lang, "gift_not_found"), show_alert=True)
        return
    await session.commit()
    await callback.message.edit_text(_gift_card(lang, tx) + "\n\n" + t(lang, "gift_rejected", id=tx.id))
    # Rad etilganda balans o'zgarmaydi — faqat band (pending) bo'lishi bekor bo'ladi.
    await _notify_sender(
        callback.bot, tx, "gift_rejected_sender", amount=amount, doctor=escape(doctor_name)
    )
    await callback.answer()
