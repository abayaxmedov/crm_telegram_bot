from __future__ import annotations

"""Оптомдан приход — TOP menejerga REAL-TIME tasdiqlash so'rovi.

Medvakil prixodni yakunlashi bilan barcha faol TOP menejerlarga karta + ✅/❌
tugmalari yuboriladi (huddi dorixona tasdig'i kabi) — bo'limni ochish shart emas.
"""

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role, User, WholesaleIncome
from app.db.repositories import get_wholesale_income
from app.i18n import normalize, t

logger = logging.getLogger(__name__)


def wi_approve_keyboard(lang: str, income_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_entity_ok"), callback_data=f"wi_ok:{income_id}"),
                InlineKeyboardButton(text=t(lang, "btn_entity_reject"), callback_data=f"wi_reject:{income_id}"),
            ]
        ]
    )


def wi_card(lang: str, income: WholesaleIncome) -> str:
    """Prixod kartasi — items/pharmacy/wholesaler/rep EAGER-LOAD bo'lishi shart."""
    pharmacy = "-"
    if income.pharmacy is not None:
        pharmacy = income.pharmacy.name
        if income.pharmacy.filial:
            pharmacy += f" (Филиал: {income.pharmacy.filial})"
    items = "\n".join(
        f"{i}. {it.drug_name} — {it.quantity} {t(lang, 'pcs')}." for i, it in enumerate(income.items, 1)
    )
    return t(
        lang,
        "wi_card",
        id=income.id,
        rep=income.rep.full_name if income.rep else "-",
        pharmacy=pharmacy,
        wholesaler=income.wholesaler.name if income.wholesaler else "-",
        date=str(income.created_at)[:16] if income.created_at else "-",
        items=items,
    )


async def notify_top_new_income(bot: Bot, session: AsyncSession, income_id: int) -> int:
    """Yangi (PENDING) prixod haqida barcha faol TOP menejerlarga so'rov yuboradi.

    Yuborilgan xabarlar soni qaytadi; bot bloklangan bo'lsa o'sha TOP o'tkazib yuboriladi."""
    income = await get_wholesale_income(session, income_id)
    if income is None or income.status != ApprovalStatus.PENDING:
        return 0

    tops = (
        (
            await session.execute(
                select(User).where(
                    User.role == Role.TOP_MANAGER, User.is_active.is_(True), User.telegram_id.is_not(None)
                )
            )
        )
        .scalars()
        .all()
    )

    sent = 0
    for top in tops:
        lang = normalize(top.language)
        try:
            await bot.send_message(
                top.telegram_id,
                t(lang, "new_wi_for_approve", card=wi_card(lang, income)),
                reply_markup=wi_approve_keyboard(lang, income.id),
            )
            sent += 1
        except Exception as exc:  # bot bloklangan / chat topilmadi
            logger.warning("TOP notify failed (top=%s): %s", top.id, exc)
    return sent
