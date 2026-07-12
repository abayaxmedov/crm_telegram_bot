from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role, WarehouseRequest, WarehouseStatus
from app.db.repositories import (
    approve_pharmacy_with_contract,
    get_doctor,
    get_pharmacy,
    get_warehouse_request,
    list_pending_doctors,
    list_pending_pharmacies,
    list_pending_warehouse_requests,
    set_doctor_status,
    set_pharmacy_status,
    set_warehouse_status,
)
from app.handlers.filters import RoleFilter
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import t, variants
from app.services.security import can_approve_entities, can_approve_warehouse

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


@router.message(F.text.in_(variants("btn_wh_approve")), RoleFilter(Role.OPERATOR, Role.OWNER))
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


# ==================== Yangi doktor/dorixona tasdig'i ====================


def _entity_kb(lang: str, kind: str, entity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_entity_ok"), callback_data=f"ent_ok:{kind}:{entity_id}"),
                InlineKeyboardButton(text=t(lang, "btn_entity_reject"), callback_data=f"ent_reject:{kind}:{entity_id}"),
            ]
        ]
    )


def _doctor_card(lang: str, doctor) -> str:
    return t(
        lang,
        "doctor_card_pending",
        id=doctor.id,
        name=safe(doctor.full_name),
        phone=safe(doctor.phone_number),
        location=safe(doctor.location_text),
        region=safe(doctor.region.name if doctor.region else None),
        author=safe(doctor.manager.full_name if doctor.manager else None),
    )


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


@router.message(F.text.in_(variants("btn_entity_approve")), RoleFilter(Role.OPERATOR, Role.OWNER))
async def entity_approve_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    doctors = await list_pending_doctors(session)
    pharmacies = await list_pending_pharmacies(session)
    if not doctors and not pharmacies:
        await message.answer(t(lang, "entity_approve_empty"))
        return
    await message.answer(t(lang, "entity_approve_header"))
    for doctor in doctors:
        await message.answer(_doctor_card(lang, doctor), reply_markup=_entity_kb(lang, "d", doctor.id))
    for pharmacy in pharmacies:
        await message.answer(_pharmacy_card(lang, pharmacy), reply_markup=_entity_kb(lang, "p", pharmacy.id))


class PharmacyApproveFlow(StatesGroup):
    """Dorixona tasdig'i: nom tekshirish -> shartnoma raqami -> shartnoma fayli."""

    name_edit = State()
    contract_number = State()
    contract_file = State()


async def _get_pending(callback: CallbackQuery, session: AsyncSession, lang: str, kind: str, entity_id: int):
    if kind == "d":
        entity = await get_doctor(session, entity_id)
    else:
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
    if not can_approve_entities(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    kind, entity_id = parts[1], int(parts[2])
    entity = await _get_pending(callback, session, lang, kind, entity_id)
    if entity is None:
        return

    if kind == "d":
        # Doktor: bir bosishda tasdiqlanadi.
        await set_doctor_status(session, doctor=entity, status=ApprovalStatus.APPROVED, operator=user)
        await session.commit()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(t(lang, "entity_approved"))
        await callback.answer()
        return

    # Dorixona: nom tekshirish -> shartnoma raqami -> shartnoma fayli.
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
    if not can_approve_entities(user.role):
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
    await state.set_state(PharmacyApproveFlow.contract_file)
    await message.answer(t(lang, "upload_contract_file"))


@router.message(PharmacyApproveFlow.contract_file, F.document)
async def pha_contract_file(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None or message.document is None:
        return
    if not can_approve_entities(user.role):
        await state.clear()
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
        contract_file_id=message.document.file_id,
        new_name=data.get("new_name"),
    )
    await session.commit()
    await state.clear()
    await message.answer(
        t(lang, "pharmacy_approved_contract", name=safe(pharmacy.name), number=safe(contract.number))
    )


@router.message(PharmacyApproveFlow.contract_file)
async def pha_contract_file_invalid(message: Message, lang: str) -> None:
    await message.answer(t(lang, "need_document"))


@router.callback_query(F.data.startswith("ent_reject:"))
async def entity_reject(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
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
    entity = await _get_pending(callback, session, lang, kind, entity_id)
    if entity is None:
        return

    if kind == "d":
        await set_doctor_status(session, doctor=entity, status=ApprovalStatus.REJECTED, operator=user)
    else:
        await set_pharmacy_status(session, pharmacy=entity, status=ApprovalStatus.REJECTED, operator=user)

    await session.commit()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t(lang, "entity_rejected"))
    await callback.answer()
