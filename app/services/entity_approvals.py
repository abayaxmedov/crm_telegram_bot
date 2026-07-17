from __future__ import annotations

"""Doktor va ЛПУ tasdig'i — TOP menejerga REAL-TIME so'rov.

MUHIM: bu tasdiq YARATISHNI TO'SMAYDI. Doktor/ЛПУ darrov yaratiladi va
ishlatilaveradi (hisobot yozish, doktorni ЛПУга bog'lash). Maqom faqat belgi:
  ⏳ kutilmoqda — yaratilgan, ishlaydi, lekin SOTUV/BALL/СОВҒА yopiq;
  ✅ tasdiqlangan — TOP menejer tasdiqlagan, hamma narsa ochiq;
  ❌ rad etilgan — sotuv/ball yopiq (hisobot baribir yoziladi).
"""

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ApprovalStatus, Doctor, Lpu, Role, User
from app.i18n import normalize, t

logger = logging.getLogger(__name__)

STATUS_BADGE = {
    ApprovalStatus.PENDING: "⏳",
    ApprovalStatus.APPROVED: "✅",
    ApprovalStatus.REJECTED: "❌",
}


def badge(status: ApprovalStatus | None) -> str:
    """Ro'yxat/karta uchun maqom belgisi."""
    return STATUS_BADGE.get(status, "⏳")


def approve_keyboard(lang: str, kind: str, entity_id: int) -> InlineKeyboardMarkup:
    """✅/❌ — kind: 'd' (doktor) yoki 'l' (ЛПУ)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_entity_ok"), callback_data=f"tapp_ok:{kind}:{entity_id}"),
                InlineKeyboardButton(text=t(lang, "btn_entity_reject"), callback_data=f"tapp_rej:{kind}:{entity_id}"),
            ]
        ]
    )


def doctor_card(lang: str, doctor: Doctor) -> str:
    """region/manager/lpu EAGER-LOAD bo'lishi shart."""
    return t(
        lang,
        "doctor_card_for_approve",
        id=doctor.id,
        name=doctor.full_name or "-",
        phone=doctor.phone_number or "-",
        lpu=doctor.lpu.name if doctor.lpu else "-",
        region=doctor.region.name if doctor.region else "-",
        author=doctor.manager.full_name if doctor.manager else "-",
    )


def lpu_card(lang: str, lpu: Lpu) -> str:
    """region/created_by EAGER-LOAD bo'lishi shart."""
    return t(
        lang,
        "lpu_card_for_approve",
        id=lpu.id,
        name=lpu.name or "-",
        address=lpu.address or "-",
        region=lpu.region.name if lpu.region else "-",
        author=lpu.created_by.full_name if lpu.created_by else "-",
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


async def _notify(bot: Bot, session: AsyncSession, *, kind: str, entity_id: int, text_key: str, card_fn, entity) -> int:
    if entity is None or entity.approval_status != ApprovalStatus.PENDING:
        return 0
    sent = 0
    for top in await _active_tops(session):
        lang = normalize(top.language)
        try:
            await bot.send_message(
                top.telegram_id,
                t(lang, text_key, card=card_fn(lang, entity)),
                reply_markup=approve_keyboard(lang, kind, entity_id),
            )
            sent += 1
        except Exception as exc:  # bot bloklangan / chat topilmadi
            logger.warning("TOP approve notify failed (top=%s, %s=%s): %s", top.id, kind, entity_id, exc)
    return sent


async def notify_top_new_doctor(bot: Bot, session: AsyncSession, doctor_id: int) -> int:
    """Yangi (PENDING) doktor haqida barcha faol TOP menejerlarga so'rov."""
    doctor = (
        await session.execute(
            select(Doctor)
            .options(selectinload(Doctor.region), selectinload(Doctor.manager), selectinload(Doctor.lpu))
            .where(Doctor.id == doctor_id)
        )
    ).scalar_one_or_none()
    return await _notify(
        bot, session, kind="d", entity_id=doctor_id,
        text_key="new_doctor_for_approve", card_fn=doctor_card, entity=doctor,
    )


async def notify_top_new_lpu(bot: Bot, session: AsyncSession, lpu_id: int) -> int:
    """Yangi (PENDING) ЛПУ haqida barcha faol TOP menejerlarga so'rov."""
    lpu = (
        await session.execute(
            select(Lpu)
            .options(selectinload(Lpu.region), selectinload(Lpu.created_by))
            .where(Lpu.id == lpu_id)
        )
    ).scalar_one_or_none()
    return await _notify(
        bot, session, kind="l", entity_id=lpu_id,
        text_key="new_lpu_for_approve", card_fn=lpu_card, entity=lpu,
    )
