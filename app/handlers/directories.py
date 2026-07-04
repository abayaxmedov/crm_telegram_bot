from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_doctor, add_pharmacy, list_doctors, list_pharmacies
from app.handlers.utils import clean_optional, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import doctors_menu, pharmacies_menu
from app.services.media import answer_media
from app.services.security import can_manage_directories

router = Router(name="directories")


class DoctorFlow(StatesGroup):
    full_name = State()
    phone = State()
    location = State()
    category = State()
    notes = State()


class PharmacyFlow(StatesGroup):
    name = State()
    phone = State()
    location = State()
    responsible = State()
    notes = State()


@router.message(F.text.in_(variants("btn_doctors")))
async def doctors_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(message, screen="doctors", text=t(lang, "doctors_text"), lang=lang, reply_markup=doctors_menu(lang))


@router.message(F.text.in_(variants("btn_doctor_add")))
async def doctor_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_directories(user.role):
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
async def doctor_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    data = await state.get_data()
    doctor = await add_doctor(
        session,
        full_name=data["full_name"],
        phone_number=data.get("phone"),
        location_text=data.get("location"),
        class_category=data.get("category"),
        manager=user,
        notes=clean_optional(message.text),
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=t(lang, "doctor_saved", id=doctor.id, name=escape(doctor.full_name)),
        lang=lang,
        reply_markup=doctors_menu(lang),
    )


@router.message(F.text.in_(variants("btn_doctors_list")))
async def doctors_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    doctors = await list_doctors(session)
    if not doctors:
        await message.answer(t(lang, "doctors_empty"), reply_markup=doctors_menu(lang))
        return
    text = t(lang, "doctors_header") + "\n\n" + "\n".join(
        f"#{doctor.id} | {safe(doctor.full_name)} | {safe(doctor.phone_number)} | {safe(doctor.class_category)}"
        for doctor in doctors
    )
    await message.answer(text, reply_markup=doctors_menu(lang))


@router.message(F.text.in_(variants("btn_pharmacies")))
async def pharmacies_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(
        message, screen="pharmacies", text=t(lang, "pharmacies_text"), lang=lang, reply_markup=pharmacies_menu(lang)
    )


@router.message(F.text.in_(variants("btn_pharmacy_add")))
async def pharmacy_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_directories(user.role):
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
    await message.answer(t(lang, "enter_location"))


@router.message(PharmacyFlow.location)
async def pharmacy_location(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(location=clean_optional(message.text))
    await state.set_state(PharmacyFlow.responsible)
    await message.answer(t(lang, "enter_responsible"))


@router.message(PharmacyFlow.responsible)
async def pharmacy_responsible(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(responsible=clean_optional(message.text))
    await state.set_state(PharmacyFlow.notes)
    await message.answer(t(lang, "enter_notes_dash"))


@router.message(PharmacyFlow.notes)
async def pharmacy_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    data = await state.get_data()
    pharmacy = await add_pharmacy(
        session,
        name=data["name"],
        phone_number=data.get("phone"),
        location_text=data.get("location"),
        responsible_person=data.get("responsible"),
        manager=user,
        notes=clean_optional(message.text),
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=t(lang, "pharmacy_saved", id=pharmacy.id, name=escape(pharmacy.name)),
        lang=lang,
        reply_markup=pharmacies_menu(lang),
    )


@router.message(F.text.in_(variants("btn_pharmacies_list")))
async def pharmacies_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    pharmacies = await list_pharmacies(session)
    if not pharmacies:
        await message.answer(t(lang, "pharmacies_empty"), reply_markup=pharmacies_menu(lang))
        return
    text = t(lang, "pharmacies_header") + "\n\n" + "\n".join(
        f"#{pharmacy.id} | {safe(pharmacy.name)} | {safe(pharmacy.phone_number)} | {safe(pharmacy.responsible_person)}"
        for pharmacy in pharmacies
    )
    await message.answer(text, reply_markup=pharmacies_menu(lang))
