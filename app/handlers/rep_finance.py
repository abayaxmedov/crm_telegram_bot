from __future__ import annotations

"""Medvakil KPI-oyligi.

Eslatma: eski pul-bonus oqimlari («Врачга пул бериш», «Админга қайтариш»)
BALL tizimi bilan almashtirilgan (app/handlers/ball.py). Bu modulda faqat
KPI asosidagi «Менинг ойлигим» qolgan."""

from datetime import datetime
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_user
from app.i18n import month_name, t, variants
from app.keyboards.reply import main_menu
from app.services.kpi import compute_kpi

router = Router(name="rep_finance")


def _money(value) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


# ==================== Моя зарплата (KPI) ====================

@router.message(F.text.in_(variants("btn_salary")), RoleFilter(Role.MANAGER))
async def rep_salary(message: Message, session: AsyncSession, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    await message.answer(t(lang, "kpi_calculating"))

    results, buckets, total = await compute_kpi(session, rep)
    now = datetime.utcnow()
    header = t(lang, "kpi_header", month=month_name(lang, now.month, now.year), name=rep.full_name)

    if not results:
        await message.answer(header + "\n\n" + t(lang, "kpi_no_plans"), reply_markup=main_menu(rep.role, lang))
        return

    blocks = "\n\n".join(t(lang, "kpi_drug_block", **r) for r in results)
    footer = t(
        lang,
        "kpi_footer",
        b1=_money(buckets[1]),
        b3=_money(buckets[3]),
        b6=_money(buckets[6]),
        total=_money(total),
    )
    await message.answer(
        header + "\n\n" + blocks + "\n\n" + "━" * 12 + "\n" + footer,
        reply_markup=main_menu(rep.role, lang),
    )
