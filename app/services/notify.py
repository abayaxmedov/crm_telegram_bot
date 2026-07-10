from __future__ import annotations

"""Doktor xabarlari va rejalashtirilgan o'chirish.

Doktor chatiga yuboriladigan xabarlar (ball tushishi/ayirilishi, tasdiqlash so'rovi)
24 soatdan keyin butunlay o'chiriladi. Tasdiqlash xabari o'chirilganda hali PENDING
bo'lgan o'tkazma EXPIRED holatiga o'tadi va yuboruvchiga xabar boradi."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.db.models import BallTxStatus, Doctor
from app.db.repositories import (
    due_deletions,
    finish_ball_transfer,
    get_ball_transaction,
    schedule_deletion,
)
from app.db.session import AsyncSessionLocal
from app.i18n import normalize, t

logger = logging.getLogger(__name__)

DOCTOR_MESSAGE_TTL = timedelta(hours=24)
SWEEP_INTERVAL_SECONDS = 60


async def send_to_doctor(
    bot: Bot,
    session,
    doctor: Doctor,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    ball_tx_id: int | None = None,
) -> bool:
    """Bog'langan doktor chatiga xabar yuboradi va 24 soatga o'chirishni rejalaydi.

    Doktor botga ulanmagan yoki yuborib bo'lmasa False qaytaradi."""
    bot_user = doctor.bot_user
    if bot_user is None or bot_user.telegram_id is None:
        return False
    try:
        message = await bot.send_message(bot_user.telegram_id, text, reply_markup=reply_markup)
    except Exception as exc:  # bot bloklangan / chat topilmadi va h.k.
        logger.warning("doctor notify failed (doctor=%s): %s", doctor.id, exc)
        return False

    await schedule_deletion(
        session,
        chat_id=message.chat.id,
        message_id=message.message_id,
        delete_at=datetime.now(timezone.utc) + DOCTOR_MESSAGE_TTL,
        ball_tx_id=ball_tx_id,
    )
    return True


async def _sweep_once(bot: Bot) -> None:
    async with AsyncSessionLocal() as session:
        rows = await due_deletions(session, datetime.now(timezone.utc))
        for row in rows:
            try:
                await bot.delete_message(chat_id=row.chat_id, message_id=row.message_id)
            except Exception:
                pass  # xabar allaqachon o'chirilgan / 48 soatdan oshgan

            # Tasdiqlash xabari edi — atomik EXPIRED'ga o'tkazamiz. finish_ball_transfer
            # PENDING bo'lmasa False qaytaradi (parallel accept yutgan) — xabar yubormaymiz.
            if row.ball_tx_id is not None:
                tx = await get_ball_transaction(session, row.ball_tx_id)
                if tx is not None and await finish_ball_transfer(session, tx, None, BallTxStatus.EXPIRED):
                    sender = tx.from_user
                    if sender is not None and sender.telegram_id is not None:
                        target = tx.to_doctor.full_name if tx.to_doctor else (
                            tx.to_user.full_name if tx.to_user else "-"
                        )
                        try:
                            await bot.send_message(
                                sender.telegram_id,
                                t(normalize(sender.language), "ball_expired_sender", name=target, amount=tx.amount),
                            )
                        except Exception:
                            pass

            await session.delete(row)
        await session.commit()


async def deletion_sweeper(bot: Bot) -> None:
    """Fon vazifasi: har daqiqada muddati kelgan xabarlarni o'chiradi."""
    while True:
        try:
            await _sweep_once(bot)
        except Exception:
            logger.exception("deletion sweeper iteration failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
