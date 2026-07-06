from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, WarehouseRequest, WarehouseStatus
from app.db.repositories import (
    get_warehouse_request,
    list_pending_warehouse_requests,
    set_warehouse_status,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user
from app.i18n import t, variants
from app.services.security import can_approve_warehouse

router = Router(name="operator")


def _card(lang: str, request: WarehouseRequest) -> str:
    if request.contract is not None:
        contract = f"Договор №{request.contract.number} ({request.contract.signed_date or '—'})"
    else:
        contract = "—"
    pharmacy = "-"
    if request.pharmacy is not None:
        pharmacy = request.pharmacy.name
        if request.pharmacy.filial:
            pharmacy += f" (Филиал: {request.pharmacy.filial})"
    items = "\n".join(
        f"{i}. {it.drug_name} — {it.quantity} {t(lang, 'pcs')}" for i, it in enumerate(request.items, 1)
    )
    return t(
        lang,
        "wh_request_card",
        id=request.id,
        rep=request.rep.full_name if request.rep else "-",
        pharmacy=pharmacy,
        contract=contract,
        date=str(request.created_at)[:16] if request.created_at else "-",
        items=items,
    )


def _approve_kb(lang: str, request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_wh_ok"), callback_data=f"wh_ok:{request_id}"),
                InlineKeyboardButton(text=t(lang, "btn_wh_reject"), callback_data=f"wh_reject:{request_id}"),
            ]
        ]
    )


@router.message(F.text.in_(variants("btn_wh_approve")), RoleFilter(Role.OPERATOR))
async def wh_approve_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    requests = await list_pending_warehouse_requests(session)
    if not requests:
        await message.answer(t(lang, "wh_approve_empty"))
        return
    await message.answer(t(lang, "wh_approve_header"))
    for request in requests:
        await message.answer(_card(lang, request), reply_markup=_approve_kb(lang, request.id))


async def _handle(callback: CallbackQuery, session: AsyncSession, lang: str, status: WarehouseStatus, result_key: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_approve_warehouse(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    request = await get_warehouse_request(session, int(callback.data.split(":", 1)[1]))
    if request is None or request.status != WarehouseStatus.NEW:
        await callback.answer(t(lang, "wh_request_not_found"), show_alert=True)
        return
    await set_warehouse_status(session, request=request, status=status, operator=user)
    await session.commit()
    await callback.message.edit_text(_card(lang, request) + "\n\n" + t(lang, result_key, id=request.id))
    await callback.answer()


@router.callback_query(F.data.startswith("wh_ok:"))
async def wh_ok(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    await _handle(callback, session, lang, WarehouseStatus.APPROVED, "wh_approved")


@router.callback_query(F.data.startswith("wh_reject:"))
async def wh_reject(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    await _handle(callback, session, lang, WarehouseStatus.REJECTED, "wh_rejected")
