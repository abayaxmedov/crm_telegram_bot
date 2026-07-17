from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role, WarehouseRequest, WarehouseStatus
from app.db.repositories import (
    approve_pharmacy_with_contract,
    get_pharmacy,
    get_warehouse_request,
    list_pending_pharmacies,
    set_pharmacy_status,
    set_warehouse_status,
    warehouse_request_total,
    warehouse_shipped_total,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import t, variants
from app.services.approvals import entity_approve_keyboard
from app.services.listing import show_list
from app.services.security import can_approve_pharmacies, can_approve_warehouse

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
    # Narxlar zayavka paytidagi to'lov shartи (100%/50%) bo'yicha snapshot qilingan.
    items = "\n".join(
        f"{i}. {it.drug_name} — {it.quantity} {t(lang, 'pcs')} × {float(it.price or 0):,.2f}"
        f" = {float((it.price or 0) * it.quantity):,.2f}"
        for i, it in enumerate(request.items, 1)
    )
    return t(
        lang,
        "wh_request_card",
        id=request.id,
        rep=request.rep.full_name if request.rep else "-",
        pharmacy=pharmacy,
        contract=contract,
        percent=int(request.payment_percent or 100),
        date=str(request.created_at)[:16] if request.created_at else "-",
        items=items,
        total=f"{float(warehouse_request_total(request)):,.2f}",
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


@router.message(F.text.in_(variants("btn_wh_approve")), RoleFilter(Role.OPERATOR, Role.OWNER))
async def wh_approve_list(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    """Tasdiq kutayotgan zayavkalar — sahifalangan ro'yxat + ИНН/nom bo'yicha qidiruv.

    Avval har zayavka alohida karta bo'lib yuborilardi (20 tagacha xabar) — operator
    puli tushgan dorixonani topolmasdi. Endi 🔍 orqali ИНН yoki dorixona nomi bilan
    topib, ID tugmasini bosadi."""
    user = await require_user(message, session)
    if user is None:
        return
    await state.clear()
    await show_list(message, session, user, lang, state, "wh_req")


@router.callback_query(F.data.startswith("wh_req:"))
async def wh_req_card(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    """Ro'yxatdagi ID tugmasi — zayavka kartasi + 🚚/❌ tugmalari."""
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
    await callback.answer()
    await callback.message.answer(_card(lang, request), reply_markup=_approve_kb(lang, request.id))


class WarehouseShipFlow(StatesGroup):
    """Otgruzka: operator har preparat uchun jo'natilgan sonni kiritadi."""

    qty = State()


async def _wh_pending(callback: CallbackQuery, session: AsyncSession, lang: str):
    """wh_ok/wh_reject uchun umumiy tekshiruv — NEW zayavkani qaytaradi."""
    user = await require_callback_user(callback, session)
    if user is None:
        return None, None
    if not can_approve_warehouse(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return None, None
    request = await get_warehouse_request(session, int(callback.data.split(":", 1)[1]))
    if request is None or request.status != WarehouseStatus.NEW:
        await callback.answer(t(lang, "wh_request_not_found"), show_alert=True)
        return None, None
    return user, request


def _ph_name(request: WarehouseRequest) -> str:
    if request.pharmacy is None:
        return "-"
    name = request.pharmacy.name
    if request.pharmacy.filial:
        name += f" (Филиал: {request.pharmacy.filial})"
    return name


async def _ask_ship_qty(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    """Navbatdagi preparat uchun jo'natilgan sonni so'raydi; ro'yxat tugasa — yakunlaydi."""
    data = await state.get_data()
    queue: list[dict] = data.get("ship_queue") or []
    index = int(data.get("ship_index") or 0)
    if index >= len(queue):
        await _finish_shipment(message, session, state, lang)
        return
    entry = queue[index]
    await state.set_state(WarehouseShipFlow.qty)
    await message.answer(
        t(
            lang,
            "wh_ship_ask",
            index=index + 1,
            count=len(queue),
            name=safe(entry["name"]),
            requested=entry["requested"],
            pcs=t(lang, "pcs"),
        )
    )


async def _finish_shipment(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    data = await state.get_data()
    await state.clear()
    user = await require_user(message, session)
    if user is None or not can_approve_warehouse(user.role):
        return
    request = await get_warehouse_request(session, int(data.get("ship_request_id") or 0))
    if request is None or request.status != WarehouseStatus.NEW:
        await message.answer(t(lang, "wh_request_not_found"))
        return
    queue: list[dict] = data.get("ship_queue") or []
    shipped = {int(e["item_id"]): int(e.get("shipped") or 0) for e in queue}
    if not any(shipped.values()):
        # Hech narsa jo'natilmagan bo'lsa zayavka NEW holida qoladi (rad etish alohida tugma).
        await message.answer(t(lang, "wh_ship_nothing"))
        return

    await set_warehouse_status(
        session, request=request, status=WarehouseStatus.APPROVED, operator=user, shipped=shipped
    )
    await session.commit()

    detail = "\n".join(
        f"{i}. {e['name']} — {t(lang, 'wh_ship_row', requested=e['requested'], shipped=int(e.get('shipped') or 0))}"
        for i, e in enumerate(queue, 1)
    )
    await message.answer(
        t(lang, "wh_ship_summary", detail=detail, total=f"{float(warehouse_shipped_total(request)):,.2f}")
        + "\n\n"
        + t(lang, "wh_approved", id=request.id)
    )


@router.callback_query(F.data.startswith("wh_ok:"))
async def wh_ok(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    """Tasdiqlash o'zi qoldiqni O'ZGARTIRMAYDI — avval otgruzka kiritiladi."""
    user, request = await _wh_pending(callback, session, lang)
    if request is None:
        return
    queue = [
        {"item_id": it.id, "name": it.drug_name, "requested": int(it.quantity)} for it in request.items
    ]
    if not queue:
        await callback.answer(t(lang, "wh_request_not_found"), show_alert=True)
        return
    await state.clear()
    await state.update_data(ship_request_id=request.id, ship_queue=queue, ship_index=0)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t(lang, "wh_ship_intro", id=request.id, pharmacy=safe(_ph_name(request))))
    await _ask_ship_qty(callback.message, session, state, lang)
    await callback.answer()


@router.message(WarehouseShipFlow.qty)
async def wh_ship_qty(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None or not can_approve_warehouse(user.role):
        await state.clear()
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(t(lang, "wh_ship_invalid"))
        return
    data = await state.get_data()
    queue: list[dict] = data.get("ship_queue") or []
    index = int(data.get("ship_index") or 0)
    if index >= len(queue):
        await state.clear()
        return
    queue[index]["shipped"] = int(raw)
    await state.update_data(ship_queue=queue, ship_index=index + 1)
    await state.set_state(None)
    await _ask_ship_qty(message, session, state, lang)


@router.callback_query(F.data.startswith("wh_reject:"))
async def wh_reject(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user, request = await _wh_pending(callback, session, lang)
    if request is None:
        return
    await state.clear()
    await set_warehouse_status(session, request=request, status=WarehouseStatus.REJECTED, operator=user)
    await session.commit()
    await callback.message.edit_text(_card(lang, request) + "\n\n" + t(lang, "wh_rejected", id=request.id))
    await callback.answer()


# ==================== Yangi doktor/dorixona tasdig'i ====================


def _pharmacy_card(lang: str, pharmacy) -> str:
    return t(
        lang,
        "pharmacy_card_pending",
        id=pharmacy.id,
        name=safe(pharmacy.name),
        phone=safe(pharmacy.phone_number),
        location=safe(pharmacy.location_text),
        region=safe(pharmacy.region.name if pharmacy.region else None),
        author=safe(pharmacy.manager.full_name if pharmacy.manager else None),
    )


@router.message(F.text.in_(variants("btn_pharmacy_approve")), RoleFilter(Role.OPERATOR, Role.OWNER))
async def pharmacy_approve_list(message: Message, session: AsyncSession, lang: str) -> None:
    """Dorixona tasdiqlash — operator (va owner)."""
    user = await require_user(message, session)
    if user is None:
        return
    pharmacies = await list_pending_pharmacies(session)
    if not pharmacies:
        await message.answer(t(lang, "pharmacy_approve_empty"))
        return
    await message.answer(t(lang, "pharmacy_approve_header"))
    for pharmacy in pharmacies:
        await message.answer(_pharmacy_card(lang, pharmacy), reply_markup=entity_approve_keyboard(lang, "p", pharmacy.id))


class PharmacyApproveFlow(StatesGroup):
    """Dorixona tasdig'i: nom tekshirish -> shartnoma raqami -> shartnoma sanasi (PDF yo'q)."""

    name_edit = State()
    contract_number = State()
    contract_date = State()


async def _get_pending(callback: CallbackQuery, session: AsyncSession, lang: str, kind: str, entity_id: int):
    """PENDING dorixonani qaytaradi (doktor tasdiqsiz yaratiladi — faqat 'p')."""
    entity = await get_pharmacy(session, entity_id)
    if entity is None or entity.approval_status != ApprovalStatus.PENDING:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return None
    return entity


@router.callback_query(F.data.startswith("ent_ok:"))
async def entity_ok(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    kind, entity_id = parts[1], int(parts[2])
    # Faqat dorixona tasdig'i qoldi (doktor tasdiqsiz yaratiladi).
    if kind != "p" or not can_approve_pharmacies(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    entity = await _get_pending(callback, session, lang, kind, entity_id)
    if entity is None:
        return

    # Dorixona: nom tekshirish -> shartnoma raqami -> shartnoma sanasi.
    # Tugmalar dorixona ID'sini olib yuradi — ikki karta parallel ochilganda
    # oxirgi bosilgan karta aniq belgilanadi (pha_id ustma-ust yozilib adashmaydi).
    await callback.message.answer(
        t(lang, "pha_check_name", name=safe(entity.name)),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=t(lang, "btn_name_ok"), callback_data=f"pha_name:ok:{entity.id}"),
                    InlineKeyboardButton(text=t(lang, "btn_name_edit"), callback_data=f"pha_name:edit:{entity.id}"),
                ]
            ]
        ),
    )
    await callback.answer()


async def _pha_name_entry(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str
) -> int | None:
    """pha_name:* callback'lari uchun umumiy tekshiruv; PENDING dorixona ID qaytaradi."""
    user = await require_callback_user(callback, session)
    if user is None:
        return None
    if not can_approve_pharmacies(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return None
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return None
    pharmacy = await get_pharmacy(session, int(parts[2]))
    if pharmacy is None or pharmacy.approval_status != ApprovalStatus.PENDING:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return None
    await state.update_data(pha_id=pharmacy.id, new_name=None)
    return pharmacy.id


@router.callback_query(F.data.startswith("pha_name:ok:"))
async def pha_name_ok(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await _pha_name_entry(callback, session, state, lang) is None:
        return
    await state.set_state(PharmacyApproveFlow.contract_number)
    await callback.message.answer(t(lang, "enter_contract_number"))
    await callback.answer()


@router.callback_query(F.data.startswith("pha_name:edit:"))
async def pha_name_edit(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await _pha_name_entry(callback, session, state, lang) is None:
        return
    await state.set_state(PharmacyApproveFlow.name_edit)
    await callback.message.answer(t(lang, "enter_new_pharmacy_name"))
    await callback.answer()


@router.message(PharmacyApproveFlow.name_edit)
async def pha_new_name(message: Message, state: FSMContext, lang: str) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer(t(lang, "name_too_short"))
        return
    await state.update_data(new_name=name)
    await state.set_state(PharmacyApproveFlow.contract_number)
    await message.answer(t(lang, "enter_contract_number"))


@router.message(PharmacyApproveFlow.contract_number)
async def pha_contract_number(message: Message, state: FSMContext, lang: str) -> None:
    number = (message.text or "").strip()
    if len(number) < 1:
        await message.answer(t(lang, "name_too_short"))
        return
    await state.update_data(contract_number=number)
    # PDF fayl SO'RALMAYDI — faqat shartnoma sanasi.
    await state.set_state(PharmacyApproveFlow.contract_date)
    await message.answer(t(lang, "enter_contract_date"))


@router.message(PharmacyApproveFlow.contract_date)
async def pha_contract_date(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_approve_pharmacies(user.role):
        await state.clear()
        return
    signed_date = (message.text or "").strip()
    if len(signed_date) < 4:
        await message.answer(t(lang, "enter_contract_date"))
        return

    data = await state.get_data()
    pharmacy = await get_pharmacy(session, data.get("pha_id"))
    if pharmacy is None or pharmacy.approval_status != ApprovalStatus.PENDING:
        await state.clear()
        await message.answer(t(lang, "entity_not_found"))
        return

    contract = await approve_pharmacy_with_contract(
        session,
        pharmacy=pharmacy,
        operator=user,
        contract_number=data["contract_number"],
        signed_date=signed_date,
        new_name=data.get("new_name"),
    )
    await session.commit()
    await state.clear()
    await message.answer(
        t(lang, "pharmacy_approved_contract", name=safe(pharmacy.name), number=safe(contract.number))
        + f" ({safe(contract.signed_date)})"
    )


@router.callback_query(F.data.startswith("ent_reject:"))
async def entity_reject(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    kind, entity_id = parts[1], int(parts[2])
    if kind != "p" or not can_approve_pharmacies(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    entity = await _get_pending(callback, session, lang, kind, entity_id)
    if entity is None:
        return

    await set_pharmacy_status(session, pharmacy=entity, status=ApprovalStatus.REJECTED, operator=user)
    await session.commit()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t(lang, "entity_rejected"))
    await callback.answer()
