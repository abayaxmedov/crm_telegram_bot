from __future__ import annotations

"""Tasdiqlash so'rovlari — operatorga REAL-TIME bildirishnoma.

Yangi dorixona yaratilishi bilan (PENDING) barcha faol operatorlarga karta +
✅/❌ tugmalari yuboriladi (huddi doktorga ball tasdig'i kabi). Operator
bildirishnomaning o'zidan tasdiqlay oladi — bo'limni ochish shart emas.
"""

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ApprovalStatus, Pharmacy, Role, User
from app.i18n import normalize, t

logger = logging.getLogger(__name__)


def entity_approve_keyboard(lang: str, kind: str, entity_id: int) -> InlineKeyboardMarkup:
    """✅ Тасдиқлаш / ❌ Рад этиш — kind: 'd' (doktor) yoki 'p' (dorixona)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_entity_ok"), callback_data=f"ent_ok:{kind}:{entity_id}"),
                InlineKeyboardButton(text=t(lang, "btn_entity_reject"), callback_data=f"ent_reject:{kind}:{entity_id}"),
            ]
        ]
    )


def _pharmacy_card(lang: str, pharmacy: Pharmacy) -> str:
    """Karta matni — region/manager EAGER-LOAD qilingan bo'lishi shart."""
    return t(
        lang,
        "pharmacy_card_pending",
        id=pharmacy.id,
        name=pharmacy.name or "-",
        phone=pharmacy.phone_number or "-",
        location=pharmacy.location_text or "-",
        region=pharmacy.region.name if pharmacy.region else "-",
        author=pharmacy.manager.full_name if pharmacy.manager else "-",
    )


async def notify_operators_new_pharmacy(bot: Bot, session: AsyncSession, pharmacy_id: int) -> int:
    """Yangi (PENDING) dorixona haqida barcha faol operatorlarga so'rov yuboradi.

    Yuborilgan xabarlar soni qaytadi. Xato bo'lsa (bot bloklangan) — o'tkazib yuboriladi."""
    pharmacy = (
        await session.execute(
            select(Pharmacy)
            .options(selectinload(Pharmacy.region), selectinload(Pharmacy.manager))
            .where(Pharmacy.id == pharmacy_id)
        )
    ).scalar_one_or_none()
    if pharmacy is None or pharmacy.approval_status != ApprovalStatus.PENDING:
        return 0

    operators = (
        await session.execute(
            select(User).where(
                User.role == Role.OPERATOR, User.is_active.is_(True), User.telegram_id.is_not(None)
            )
        )
    ).scalars().all()

    sent = 0
    for op in operators:
        lang = normalize(op.language)
        try:
            await bot.send_message(
                op.telegram_id,
                t(lang, "new_pharmacy_for_approve", card=_pharmacy_card(lang, pharmacy)),
                reply_markup=entity_approve_keyboard(lang, "p", pharmacy.id),
            )
            sent += 1
        except Exception as exc:  # bot bloklangan / chat topilmadi
            logger.warning("operator notify failed (op=%s): %s", op.id, exc)
    return sent
