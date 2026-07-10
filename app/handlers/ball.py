from __future__ import annotations

"""Ball (aksiya ballari) bo'limi.

Zanjir: owner (emissiya) -> TOP menejer -> regional menejer -> medvakil -> doktor.
Har o'tkazma qabul qiluvchi tasdig'i bilan kuchga kiradi. Doktorga yuborilgan
tasdiqlash xabari 24 soatda o'chadi va o'tkazma muddati tugaydi."""

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from datetime import datetime, timezone

from app.db.models import ApprovalStatus, BallTxKind, BallTxStatus, Doctor, Role, User
from app.db.repositories import (
    available_ball,
    accept_ball_transfer,
    ball_balances_overview,
    ball_transactions_in_period,
    create_ball_transfer,
    doctors_for_ball_transfer,
    finish_ball_transfer,
    get_ball_balance,
    get_ball_transaction,
    get_doctor_with_user,
    pending_outgoing_ball,
    period_window,
    schedule_deletion,
)
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import ball_kind_label, ball_status_label, normalize, role_label, t, variants
from app.keyboards.reply import (
    ball_accept_keyboard,
    ball_inline_keyboard,
    entities_inline,
    excel_periods_keyboard,
)
from app.services.excel import build_xlsx
from app.services.notify import DOCTOR_MESSAGE_TTL, send_to_doctor
from app.services.security import ball_transfer_target_role, can_use_ball, can_view_hierarchy_reports

router = Router(name="ball")


class BallSendFlow(StatesGroup):
    amount = State()


def _valid_user_target(sender: User, target: User | None) -> bool:
    """Zanjir qoidasi: callback_data soxtalashtirilishiga qarshi qat'iy tekshiruv.

    owner->TOP, TOP->regional, regional->o'z regioni medvakili. Aks holda rad."""
    if target is None or not target.is_active or target.telegram_id is None:
        return False
    if target.role != ball_transfer_target_role(sender.role):
        return False
    if sender.role == Role.REGIONAL_MANAGER and target.region_id != sender.region_id:
        return False
    return True


def _valid_doctor_target(sender: User, doctor: Doctor | None) -> bool:
    """Doktorga faqat MEDVAKIL, o'z regionidagi, APPROVED va botga ulangan doktorga yuboradi."""
    if sender.role != Role.MANAGER:
        return False
    if doctor is None or doctor.approval_status != ApprovalStatus.APPROVED:
        return False
    if doctor.region_id != sender.region_id:
        return False
    return doctor.bot_user is not None and doctor.bot_user.telegram_id is not None


def _tx_party_name(tx, side: str) -> str:
    if side == "from":
        return tx.from_user.full_name if tx.from_user else "—"
    if tx.to_user is not None:
        return tx.to_user.full_name
    if tx.to_doctor is not None:
        return tx.to_doctor.full_name
    return "—"


# ==================== Panel ====================


@router.message(F.text.in_(variants("btn_ball")))
async def ball_panel(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_use_ball(user.role):
        await message.answer(t(lang, "ball_no_perm"))
        return
    await state.clear()

    if user.role == Role.OWNER:
        text = t(lang, "ball_balance_owner")
    else:
        text = t(lang, "ball_balance_text", balance=int(user.ball_balance or 0))
        pending = await pending_outgoing_ball(session, user)
        if pending > 0:
            text += "\n" + t(lang, "ball_pending_note", pending=pending)
    await message.answer(text, reply_markup=ball_inline_keyboard(lang))


# ==================== Yuborish ====================


@router.callback_query(F.data == "ball:send")
async def ball_send_start(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_use_ball(user.role):
        await callback.answer(t(lang, "ball_no_perm"), show_alert=True)
        return

    if user.role == Role.MANAGER:
        doctors = await doctors_for_ball_transfer(session, user)
        if not doctors:
            await callback.message.answer(t(lang, "ball_no_linked_doctors"))
            await callback.answer()
            return
        await callback.message.answer(
            t(lang, "ball_choose_recipient"),
            reply_markup=entities_inline([(d.id, d.full_name) for d in doctors], "ball_to_doc"),
        )
        await callback.answer()
        return

    target_role = ball_transfer_target_role(user.role)
    if target_role is None:
        await callback.answer(t(lang, "ball_no_perm"), show_alert=True)
        return

    query = (
        select(User)
        .options(selectinload(User.region))
        .where(User.role == target_role, User.is_active.is_(True), User.telegram_id.is_not(None))
        .order_by(User.full_name)
    )
    if user.role == Role.REGIONAL_MANAGER:
        # Regional menejer faqat o'z regionidagi medvakillarga yuboradi.
        query = query.where(User.region_id == user.region_id)
    recipients = list((await session.execute(query)).scalars())
    if not recipients:
        await callback.message.answer(t(lang, "ball_no_recipients"))
        await callback.answer()
        return

    labels = [
        (u.id, f"{u.full_name}" + (f" ({u.region.name})" if u.region else "")) for u in recipients
    ]
    await callback.message.answer(
        t(lang, "ball_choose_recipient"), reply_markup=entities_inline(labels, "ball_to_user")
    )
    await callback.answer()


async def _ask_amount(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext, user: User, lang: str
) -> None:
    await state.set_state(BallSendFlow.amount)
    if user.role == Role.OWNER:
        await callback.message.answer(t(lang, "ball_enter_amount_owner"))
    else:
        available = await available_ball(session, user)
        await callback.message.answer(t(lang, "ball_enter_amount", available=available))
    await callback.answer()


@router.callback_query(F.data.startswith("ball_to_user:"))
async def ball_pick_user(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_use_ball(user.role):
        await callback.answer(t(lang, "ball_no_perm"), show_alert=True)
        return
    target = (
        await session.execute(select(User).where(User.id == int(callback.data.split(":", 1)[1])))
    ).scalar_one_or_none()
    # Soxta callback_data'ga qarshi: zanjir/region qoidasi shu yerda ham tekshiriladi.
    if not _valid_user_target(user, target):
        await callback.answer(t(lang, "ball_no_recipients"), show_alert=True)
        return
    await state.update_data(to_user_id=target.id, to_doctor_id=None)
    await _ask_amount(callback, session, state, user, lang)


@router.callback_query(F.data.startswith("ball_to_doc:"))
async def ball_pick_doctor(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_use_ball(user.role):
        await callback.answer(t(lang, "ball_no_perm"), show_alert=True)
        return
    doctor = await get_doctor_with_user(session, int(callback.data.split(":", 1)[1]))
    if not _valid_doctor_target(user, doctor):
        await callback.answer(t(lang, "ball_no_linked_doctors"), show_alert=True)
        return
    await state.update_data(to_doctor_id=doctor.id, to_user_id=None)
    await _ask_amount(callback, session, state, user, lang)


@router.message(BallSendFlow.amount)
async def ball_amount(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    sender = await require_user(message, session)
    if sender is None:
        return

    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(t(lang, "ball_amount_invalid"))
        return
    amount = int(raw)

    if sender.role != Role.OWNER:
        available = await available_ball(session, sender)
        if amount > available:
            await message.answer(t(lang, "ball_insufficient", available=available))
            return

    data = await state.get_data()
    to_user = None
    to_doctor = None
    recipient_chat_id = None
    recipient_lang = lang
    recipient_name = "-"

    # Qabul qiluvchini QAYTA validatsiya qilamiz (state eskirgan/soxta bo'lishi mumkin).
    if data.get("to_user_id"):
        to_user = (
            await session.execute(select(User).where(User.id == data["to_user_id"]))
        ).scalar_one_or_none()
        if not _valid_user_target(sender, to_user):
            await state.clear()
            await message.answer(t(lang, "ball_no_recipients"))
            return
        recipient_chat_id = to_user.telegram_id
        recipient_lang = normalize(to_user.language)
        recipient_name = to_user.full_name
    elif data.get("to_doctor_id"):
        to_doctor = await get_doctor_with_user(session, data["to_doctor_id"])
        if not _valid_doctor_target(sender, to_doctor):
            await state.clear()
            await message.answer(t(lang, "ball_no_linked_doctors"))
            return
        recipient_lang = normalize(to_doctor.bot_user.language)
        recipient_name = to_doctor.full_name
    else:
        await state.clear()
        return

    tx = await create_ball_transfer(session, sender=sender, amount=amount, to_user=to_user, to_doctor=to_doctor)
    # Avval commit — qabul qiluvchi tugmani bosganда tx bazada bo'lishi shart.
    await session.commit()
    await state.clear()

    prompt = t(
        recipient_lang,
        "ball_accept_prompt",
        from_name=escape(sender.full_name),
        amount=amount,
    )

    delivered = False
    if to_doctor is not None:
        # Doktor xabari 24 soatda o'chadi; o'chganda pending o'tkazma EXPIRED bo'ladi.
        delivered = await send_to_doctor(
            message.bot,
            session,
            to_doctor,
            prompt,
            reply_markup=ball_accept_keyboard(recipient_lang, tx.id),
            ball_tx_id=tx.id,
        )
        if delivered:
            await session.commit()
    else:
        try:
            sent = await message.bot.send_message(
                recipient_chat_id, prompt, reply_markup=ball_accept_keyboard(recipient_lang, tx.id)
            )
            # Xodim-qabul qiluvchi uchun ham 24 soatlik muddat: tasdiqlanmasa EXPIRED
            # bo'lib, yuboruvchining available_ball'i abadiy qulflanib qolmaydi.
            await schedule_deletion(
                session,
                chat_id=sent.chat.id,
                message_id=sent.message_id,
                delete_at=datetime.now(timezone.utc) + DOCTOR_MESSAGE_TTL,
                ball_tx_id=tx.id,
            )
            await session.commit()
            delivered = True
        except Exception:
            delivered = False

    if not delivered:
        await finish_ball_transfer(session, tx, sender, BallTxStatus.REJECTED)
        await session.commit()
        await message.answer(t(lang, "ball_recipient_unreachable"))
        return

    await message.answer(t(lang, "ball_request_sent", name=escape(recipient_name), amount=amount))


# ==================== Qabul qilish / rad etish ====================


def _is_recipient(tx, user: User) -> bool:
    if tx.to_user_id is not None:
        return tx.to_user_id == user.id
    if tx.to_doctor is not None:
        return tx.to_doctor.user_id == user.id
    return False


async def _notify_sender(callback: CallbackQuery, tx, key: str, recipient_name: str) -> None:
    sender = tx.from_user
    if sender is None or sender.telegram_id is None:
        return
    try:
        await callback.bot.send_message(
            sender.telegram_id,
            t(normalize(sender.language), key, name=escape(recipient_name), amount=tx.amount),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("ball_acc:"))
async def ball_accept(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    tx = await get_ball_transaction(session, int(callback.data.split(":", 1)[1]))
    if tx is None or tx.status != BallTxStatus.PENDING:
        await callback.answer(t(lang, "ball_tx_not_found"), show_alert=True)
        return
    if not _is_recipient(tx, user):
        await callback.answer(t(lang, "ball_not_yours"), show_alert=True)
        return

    result = await accept_ball_transfer(session, tx, user)
    await session.commit()

    if result == "conflict":
        # Allaqachon qabul/rad/expire qilingan (parallel bosish, sweeper poygasi).
        await callback.answer(t(lang, "ball_tx_not_found"), show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    recipient_name = _tx_party_name(tx, "to")
    if result == "insufficient":
        await callback.message.answer(t(lang, "ball_autoreject_insufficient"))
        await _notify_sender(callback, tx, "ball_rejected_sender", recipient_name)
        await callback.answer()
        return

    # Atomik UPDATE'dan keyin ORM obyekt eskirgan — balансni bazadan o'qiymiz.
    if tx.to_user_id is not None:
        new_balance = await get_ball_balance(session, user_id=tx.to_user_id)
    else:
        new_balance = await get_ball_balance(session, doctor_id=tx.to_doctor_id)
    confirmation = await callback.message.answer(
        t(lang, "ball_accepted_recipient", amount=tx.amount, balance=new_balance)
    )
    # Doktor chatidagi tasdiq xabari ham 1 kunda o'chadi.
    if tx.to_doctor is not None:
        await schedule_deletion(
            session,
            chat_id=confirmation.chat.id,
            message_id=confirmation.message_id,
            delete_at=datetime.now(timezone.utc) + DOCTOR_MESSAGE_TTL,
        )
        await session.commit()

    await _notify_sender(callback, tx, "ball_accepted_sender", recipient_name)
    await callback.answer()


@router.callback_query(F.data.startswith("ball_rej:"))
async def ball_reject(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    tx = await get_ball_transaction(session, int(callback.data.split(":", 1)[1]))
    if tx is None or tx.status != BallTxStatus.PENDING:
        await callback.answer(t(lang, "ball_tx_not_found"), show_alert=True)
        return
    if not _is_recipient(tx, user):
        await callback.answer(t(lang, "ball_not_yours"), show_alert=True)
        return

    applied = await finish_ball_transfer(session, tx, user, BallTxStatus.REJECTED)
    await session.commit()
    if not applied:
        await callback.answer(t(lang, "ball_tx_not_found"), show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t(lang, "ball_rejected_recipient"))
    await _notify_sender(callback, tx, "ball_rejected_sender", _tx_party_name(tx, "to"))
    await callback.answer()


# ==================== Hisobot ====================


@router.callback_query(F.data == "ball:report")
async def ball_report(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not (can_use_ball(user.role) or can_view_hierarchy_reports(user.role)):
        await callback.answer(t(lang, "ball_no_perm"), show_alert=True)
        return

    users, doctors = await ball_balances_overview(session, user)
    start, end = period_window("30d")
    txs = await ball_transactions_in_period(session, user, start, end)

    inflow = sum(x.amount for x in txs if x.kind == BallTxKind.MINT and x.status == BallTxStatus.ACCEPTED)
    outflow = sum(x.amount for x in txs if x.kind == BallTxKind.TRANSFER and x.status == BallTxStatus.ACCEPTED)
    deducted = sum(x.amount for x in txs if x.kind == BallTxKind.SALE_DEDUCT)

    lines = [t(lang, "ball_report_header"), ""]
    lines.append(t(lang, "ball_turnover_line", inflow=inflow, outflow=outflow, deducted=deducted))
    if users:
        lines.append("")
        lines.append(t(lang, "ball_balances_users"))
        lines.extend(
            f"• {safe(u.full_name)} ({role_label(lang, u.role)}): <b>{int(u.ball_balance or 0)}</b>"
            for u in users[:15]
        )
    if doctors:
        lines.append("")
        lines.append(t(lang, "ball_balances_doctors"))
        lines.extend(f"• {safe(d.full_name)}: <b>{int(d.ball_balance or 0)}</b>" for d in doctors[:15])

    await callback.message.answer("\n".join(lines), reply_markup=excel_periods_keyboard(lang, "ball_xlsx"))
    await callback.answer()


@router.callback_query(F.data.startswith("ball_xlsx:"))
async def ball_report_xlsx(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not (can_use_ball(user.role) or can_view_hierarchy_reports(user.role)):
        await callback.answer(t(lang, "ball_no_perm"), show_alert=True)
        return

    period = callback.data.split(":", 1)[1]
    start, end = period_window(period)
    users, doctors = await ball_balances_overview(session, user)
    txs = await ball_transactions_in_period(session, user, start, end)

    sheets = [
        (
            "Ходимлар баланси",
            ["Ходим", "Роль", "Регион", "Балл баланс"],
            [
                [u.full_name, role_label(lang, u.role), u.region.name if u.region else "-", int(u.ball_balance or 0)]
                for u in users
            ],
        ),
        (
            "Докторлар баланси",
            ["Доктор", "Регион", "Балл баланс"],
            [[d.full_name, d.region.name if d.region else "-", int(d.ball_balance or 0)] for d in doctors],
        ),
        (
            "Ҳаракатлар",
            ["Сана", "Тури", "Кимдан", "Кимга", "Балл", "Ҳолат"],
            [
                [
                    str(x.created_at)[:16],
                    ball_kind_label(lang, x.kind),
                    _tx_party_name(x, "from"),
                    _tx_party_name(x, "to"),
                    x.amount,
                    ball_status_label(lang, x.status),
                ]
                for x in txs
            ],
        ),
    ]
    data = build_xlsx(sheets)
    await callback.answer()
    await callback.message.answer_document(
        document=BufferedInputFile(data, filename=f"ball_report_{period}.xlsx"),
        caption=t(lang, "excel_caption_ball", period=t(lang, f"period_{period}")),
    )
