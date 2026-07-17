from __future__ import annotations

"""TOP menejer: doktor va ЛПУ maqomini tasdiqlash.

Tasdiq YARATISHNI TO'SMAYDI — doktor/ЛПУ tasdiqsiz ham yaratiladi va hisobot
yoziladi. Tasdiq faqat SOTUV/BALL/СОВҒА uchun darvoza (`only_approved` ro'yxatlari).
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role
from app.db.repositories import (
    get_doctor_full,
    get_lpu_full,
    list_pending_doctors,
    list_pending_lpus,
    set_doctor_status,
    set_lpu_status,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user
from app.i18n import t, variants
from app.services.entity_approvals import approve_keyboard, doctor_card, lpu_card
from app.services.security import can_approve_entities

router = Router(name="top_approvals")


@router.message(F.text.in_(variants("btn_entity_approve")), RoleFilter(Role.TOP_MANAGER, Role.OWNER))
async def approve_list(message: Message, session: AsyncSession, lang: str) -> None:
    """Tasdiq kutayotgan ЛПУ va doktorlar (ЛПУ avval — doktor unga bog'lanadi)."""
    user = await require_user(message, session)
    if user is None:
        return
    if not can_approve_entities(user.role):
        await message.answer(t(lang, "section_closed"))
        return

    lpus = await list_pending_lpus(session)
    doctors = await list_pending_doctors(session)
    if not lpus and not doctors:
        await message.answer(t(lang, "entity_approve_empty"))
        return

    await message.answer(t(lang, "entity_approve_header", lpus=len(lpus), doctors=len(doctors)))
    for lpu in lpus:
        await message.answer(lpu_card(lang, lpu), reply_markup=approve_keyboard(lang, "l", lpu.id))
    for doctor in doctors:
        await message.answer(doctor_card(lang, doctor), reply_markup=approve_keyboard(lang, "d", doctor.id))


async def _decide(callback: CallbackQuery, session: AsyncSession, lang: str, status: ApprovalStatus) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_approve_entities(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    kind, entity_id = parts[1], int(parts[2])

    if kind == "d":
        entity = await get_doctor_full(session, entity_id)
        if entity is None or entity.approval_status != ApprovalStatus.PENDING:
            await callback.answer(t(lang, "entity_already_decided"), show_alert=True)
            return
        # Parallel TOP'lar poygasida faqat bittasi yutadi.
        if not await set_doctor_status(session, doctor=entity, status=status, operator=user):
            await callback.answer(t(lang, "entity_already_decided"), show_alert=True)
            return
        card = doctor_card(lang, entity)
    elif kind == "l":
        entity = await get_lpu_full(session, entity_id)
        if entity is None or entity.approval_status != ApprovalStatus.PENDING:
            await callback.answer(t(lang, "entity_already_decided"), show_alert=True)
            return
        if not await set_lpu_status(session, lpu=entity, status=status, actor=user):
            await callback.answer(t(lang, "entity_already_decided"), show_alert=True)
            return
        card = lpu_card(lang, entity)
    else:
        await callback.answer()
        return

    await session.commit()
    result_key = "entity_approved_ok" if status == ApprovalStatus.APPROVED else "entity_rejected_ok"
    await callback.message.edit_text(card + "\n\n" + t(lang, result_key))
    await callback.answer()


@router.callback_query(F.data.startswith("tapp_ok:"))
async def entity_approve(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    await _decide(callback, session, lang, ApprovalStatus.APPROVED)


@router.callback_query(F.data.startswith("tapp_rej:"))
async def entity_reject(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    await _decide(callback, session, lang, ApprovalStatus.REJECTED)
