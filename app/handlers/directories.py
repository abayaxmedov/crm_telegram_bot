from __future__ import annotations

from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus
from app.db.repositories import (
    add_doctor,
    add_pharmacy,
    get_region,
    list_doctors_visible,
    list_pharmacies_visible,
    list_regions,
)
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import doctors_menu, entities_inline, location_request_keyboard, pharmacies_menu
from app.services.excel import build_xlsx
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import (
    can_add_directories,
    can_view_directories,
    can_view_pharmacies,
    creates_entity_approved,
)

router = Router(name="directories")


class DoctorFlow(StatesGroup):
    full_name = State()
    phone = State()
    location = State()
    category = State()
    notes = State()
    region = State()


class PharmacyFlow(StatesGroup):
    name = State()
    phone = State()
    location = State()
    responsible = State()
    inn = State()
    filial = State()
    notes = State()


async def _ask_region(message: Message, session: AsyncSession, state: FSMContext, lang: str, next_state: State, prefix: str) -> bool:
    """Region ro'yxatini inline ko'rsatadi. Region bo'lmasa False qaytaradi."""
    regions = await list_regions(session)
    if not regions:
        await message.answer(t(lang, "no_regions_create_first"))
        await state.clear()
        return False
    await state.set_state(next_state)
    await message.answer(
        t(lang, "choose_region"),
        reply_markup=entities_inline([(r.id, r.name) for r in regions], prefix),
    )
    return True


# ==================== Doktorlar ====================


@router.message(F.text.in_(variants("btn_doctors")))
async def doctors_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_directories(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await answer_media(
        message,
        screen="doctors",
        text=t(lang, "doctors_text"),
        lang=lang,
        reply_markup=doctors_menu(lang, can_add=can_add_directories(user.role)),
    )


@router.message(F.text.in_(variants("btn_doctor_add")))
async def doctor_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_add_directories(user.role):
        await message.answer(t(lang, "no_perm_doctor_add"))
        return
    await state.set_state(DoctorFlow.full_name)
    await message.answer(t(lang, "enter_doctor_fullname"))


@router.message(DoctorFlow.full_name)
async def doctor_full_name(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(full_name=(message.text or "").strip())
    await state.set_state(DoctorFlow.phone)
    await message.answer(t(lang, "enter_phone"))


@router.message(DoctorFlow.phone)
async def doctor_phone(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(phone=clean_optional(message.text))
    await state.set_state(DoctorFlow.location)
    await message.answer(t(lang, "enter_location"))


@router.message(DoctorFlow.location)
async def doctor_location(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(location=clean_optional(message.text))
    await state.set_state(DoctorFlow.category)
    await message.answer(t(lang, "enter_category"))


@router.message(DoctorFlow.category)
async def doctor_category(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(category=clean_optional(message.text))
    await state.set_state(DoctorFlow.notes)
    await message.answer(t(lang, "enter_notes_dash"))


@router.message(DoctorFlow.notes)
async def doctor_notes(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await state.update_data(notes=clean_optional(message.text))
    await _ask_region(message, session, state, lang, DoctorFlow.region, "doc_region")


@router.callback_query(DoctorFlow.region, F.data.startswith("doc_region:"))
async def doctor_finish(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    region_id = int(callback.data.split(":", 1)[1]) if callback.data else 0
    region = await get_region(session, region_id)
    if region is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()

    data = await state.get_data()
    status = ApprovalStatus.APPROVED if creates_entity_approved(user.role) else ApprovalStatus.PENDING
    doctor = await add_doctor(
        session,
        full_name=data["full_name"],
        phone_number=data.get("phone"),
        location_text=data.get("location"),
        class_category=data.get("category"),
        manager=user,
        notes=data.get("notes"),
        region_id=region_id,
        approval_status=status,
    )
    await session.commit()
    await state.clear()

    if status == ApprovalStatus.APPROVED:
        text = t(lang, "doctor_saved", id=doctor.id, name=escape(doctor.full_name))
    else:
        text = t(lang, "entity_pending")
    await answer_media(callback.message, screen="done", text=text, lang=lang, reply_markup=doctors_menu(lang))


@router.message(F.text.in_(variants("btn_doctors_list")))
async def doctors_list(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_directories(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await show_list(message, session, user, lang, state, "doc_dir")


@router.message(F.text.in_(variants("btn_doctors_excel")))
async def doctors_excel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_directories(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    doctors = await list_doctors_visible(session, user, limit=5000)
    rows = [
        [
            d.id,
            d.full_name,
            d.phone_number,
            d.region.name if d.region else "-",
            d.class_category,
            d.location_text,
            d.manager.full_name if d.manager else "-",
            int(d.ball_balance or 0),
            str(d.created_at)[:16] if d.created_at else "-",
        ]
        for d in doctors
    ]
    data = build_xlsx(
        [("Докторлар", ["ID", "ФИО", "Телефон", "Регион", "Категория", "Манзил", "Масъул", "Балл баланс", "Яратилган"], rows)]
    )
    await message.answer_document(
        document=BufferedInputFile(data, filename="doctors.xlsx"),
        caption=t(lang, "excel_caption_doctors"),
    )


# ==================== Dorixonalar ====================


@router.message(F.text.in_(variants("btn_pharmacies")))
async def pharmacies_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_pharmacies(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await answer_media(
        message,
        screen="pharmacies",
        text=t(lang, "pharmacies_text"),
        lang=lang,
        reply_markup=pharmacies_menu(lang, can_add=can_add_directories(user.role)),
    )


@router.message(F.text.in_(variants("btn_pharmacy_add")))
async def pharmacy_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_add_directories(user.role):
        await message.answer(t(lang, "no_perm_pharmacy_add"))
        return
    await state.set_state(PharmacyFlow.name)
    await message.answer(t(lang, "enter_pharmacy_name"))


@router.message(PharmacyFlow.name)
async def pharmacy_name(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(PharmacyFlow.phone)
    await message.answer(t(lang, "enter_phone"))


@router.message(PharmacyFlow.phone)
async def pharmacy_phone(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(phone=clean_optional(message.text))
    await state.set_state(PharmacyFlow.location)
    # Joylashuvni ulashish tugmasi bilan (matn ham kiritish mumkin).
    await message.answer(t(lang, "enter_location_geo"), reply_markup=location_request_keyboard(lang))


@router.message(PharmacyFlow.location, F.location)
async def pharmacy_location_geo(message: Message, state: FSMContext, lang: str) -> None:
    loc = message.location
    await state.update_data(
        location=None, lat=str(loc.latitude), lng=str(loc.longitude)
    )
    await state.set_state(PharmacyFlow.responsible)
    await message.answer(t(lang, "enter_responsible"), reply_markup=ReplyKeyboardRemove())


@router.message(PharmacyFlow.location)
async def pharmacy_location(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(location=clean_optional(message.text), lat=None, lng=None)
    await state.set_state(PharmacyFlow.responsible)
    await message.answer(t(lang, "enter_responsible"), reply_markup=ReplyKeyboardRemove())


@router.message(PharmacyFlow.responsible)
async def pharmacy_responsible(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(responsible=clean_optional(message.text))
    await state.set_state(PharmacyFlow.inn)
    await message.answer(t(lang, "enter_pharmacy_inn"))


@router.message(PharmacyFlow.inn)
async def pharmacy_inn(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(inn=clean_optional(message.text))
    await state.set_state(PharmacyFlow.filial)
    await message.answer(t(lang, "enter_pharmacy_filial"))


@router.message(PharmacyFlow.filial)
async def pharmacy_filial(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(filial=clean_optional(message.text))
    await state.set_state(PharmacyFlow.notes)
    await message.answer(t(lang, "enter_notes_dash"))


@router.message(PharmacyFlow.notes)
async def pharmacy_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return

    data = await state.get_data()
    status = ApprovalStatus.APPROVED if creates_entity_approved(user.role) else ApprovalStatus.PENDING
    # Region tanlanmaydi — apteka yaratuvchi (menejer/medvakil) regioniga bog'lanadi.
    pharmacy = await add_pharmacy(
        session,
        name=data["name"],
        phone_number=data.get("phone"),
        location_text=data.get("location"),
        responsible_person=data.get("responsible"),
        manager=user,
        notes=clean_optional(message.text),
        inn=data.get("inn"),
        filial=data.get("filial"),
        region_id=user.region_id,
        approval_status=status,
        latitude=Decimal(data["lat"]) if data.get("lat") else None,
        longitude=Decimal(data["lng"]) if data.get("lng") else None,
    )
    await session.commit()
    await state.clear()

    if status == ApprovalStatus.APPROVED:
        text = t(lang, "pharmacy_saved", id=pharmacy.id, name=escape(pharmacy.name))
    else:
        text = t(lang, "entity_pending")
    await answer_media(
        message,
        screen="done",
        text=text,
        lang=lang,
        reply_markup=pharmacies_menu(lang, can_add=can_add_directories(user.role)),
    )


@router.message(F.text.in_(variants("btn_pharmacies_list")))
async def pharmacies_list(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_pharmacies(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await show_list(message, session, user, lang, state, "ph_dir")


@router.message(F.text.in_(variants("btn_pharmacies_excel")))
async def pharmacies_excel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_pharmacies(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    pharmacies = await list_pharmacies_visible(session, user, limit=5000)
    rows = [
        [
            p.id,
            p.name,
            p.filial,
            p.inn,
            p.phone_number,
            p.region.name if p.region else "-",
            p.responsible_person,
            p.location_text,
            p.manager.full_name if p.manager else "-",
            str(p.created_at)[:16] if p.created_at else "-",
        ]
        for p in pharmacies
    ]
    data = build_xlsx(
        [
            (
                "Дорихоналар",
                ["ID", "Номи", "Филиал", "ИНН", "Телефон", "Регион", "Масъул шахс", "Манзил", "Ким киритган", "Яратилган"],
                rows,
            )
        ]
    )
    await message.answer_document(
        document=BufferedInputFile(data, filename="pharmacies.xlsx"),
        caption=t(lang, "excel_caption_pharmacies"),
    )
