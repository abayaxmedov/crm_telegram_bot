from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_doctor, add_pharmacy, list_doctors, list_pharmacies
from app.handlers.utils import clean_optional, require_user, safe
from app.keyboards.reply import (
    BTN_DOCTORS,
    BTN_PHARMACIES,
    doctors_menu,
    pharmacies_menu,
)
from app.services.media import answer_media
from app.services.security import can_manage_directories
from app.texts import DOCTORS_TEXT, PHARMACIES_TEXT

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


@router.message(F.text == BTN_DOCTORS)
async def doctors_panel(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(message, screen="doctors", text=DOCTORS_TEXT, reply_markup=doctors_menu())


@router.message(F.text == "➕ Vrach qo‘shish")
async def doctor_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_directories(user.role):
        await message.answer("Vrach qo'shish uchun ruxsat yo'q.")
        return
    await state.set_state(DoctorFlow.full_name)
    await message.answer("Vrachning to'liq ism-familiyasini kiriting:")


@router.message(DoctorFlow.full_name)
async def doctor_full_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=(message.text or "").strip())
    await state.set_state(DoctorFlow.phone)
    await message.answer("Telefon raqami:")


@router.message(DoctorFlow.phone)
async def doctor_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=clean_optional(message.text))
    await state.set_state(DoctorFlow.location)
    await message.answer("Lokatsiya yoki manzil:")


@router.message(DoctorFlow.location)
async def doctor_location(message: Message, state: FSMContext) -> None:
    await state.update_data(location=clean_optional(message.text))
    await state.set_state(DoctorFlow.category)
    await message.answer("Sinf/kategoriya:")


@router.message(DoctorFlow.category)
async def doctor_category(message: Message, state: FSMContext) -> None:
    await state.update_data(category=clean_optional(message.text))
    await state.set_state(DoctorFlow.notes)
    await message.answer("Izoh. Agar izoh yo'q bo'lsa `-` yuboring:")


@router.message(DoctorFlow.notes)
async def doctor_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
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
        text=f"<b>Vrach saqlandi:</b> #{doctor.id} {escape(doctor.full_name)}",
        reply_markup=doctors_menu(),
    )


@router.message(F.text == "📋 Vrachlar ro‘yxati")
async def doctors_list(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    doctors = await list_doctors(session)
    if not doctors:
        await message.answer("Vrachlar ro'yxati hali bo'sh.", reply_markup=doctors_menu())
        return
    text = "<b>Vrachlar</b>\n\n" + "\n".join(
        f"#{doctor.id} | {safe(doctor.full_name)} | {safe(doctor.phone_number)} | {safe(doctor.class_category)}"
        for doctor in doctors
    )
    await message.answer(text, reply_markup=doctors_menu())


@router.message(F.text == BTN_PHARMACIES)
async def pharmacies_panel(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(message, screen="pharmacies", text=PHARMACIES_TEXT, reply_markup=pharmacies_menu())


@router.message(F.text == "➕ Apteka qo‘shish")
async def pharmacy_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_directories(user.role):
        await message.answer("Apteka qo'shish uchun ruxsat yo'q.")
        return
    await state.set_state(PharmacyFlow.name)
    await message.answer("Apteka nomini kiriting:")


@router.message(PharmacyFlow.name)
async def pharmacy_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(PharmacyFlow.phone)
    await message.answer("Telefon raqami:")


@router.message(PharmacyFlow.phone)
async def pharmacy_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=clean_optional(message.text))
    await state.set_state(PharmacyFlow.location)
    await message.answer("Lokatsiya yoki manzil:")


@router.message(PharmacyFlow.location)
async def pharmacy_location(message: Message, state: FSMContext) -> None:
    await state.update_data(location=clean_optional(message.text))
    await state.set_state(PharmacyFlow.responsible)
    await message.answer("Mas'ul shaxs:")


@router.message(PharmacyFlow.responsible)
async def pharmacy_responsible(message: Message, state: FSMContext) -> None:
    await state.update_data(responsible=clean_optional(message.text))
    await state.set_state(PharmacyFlow.notes)
    await message.answer("Izoh. Agar izoh yo'q bo'lsa `-` yuboring:")


@router.message(PharmacyFlow.notes)
async def pharmacy_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
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
        text=f"<b>Apteka saqlandi:</b> #{pharmacy.id} {escape(pharmacy.name)}",
        reply_markup=pharmacies_menu(),
    )


@router.message(F.text == "📋 Aptekalar ro‘yxati")
async def pharmacies_list(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    pharmacies = await list_pharmacies(session)
    if not pharmacies:
        await message.answer("Aptekalar ro'yxati hali bo'sh.", reply_markup=pharmacies_menu())
        return
    text = "<b>Aptekalar</b>\n\n" + "\n".join(
        f"#{pharmacy.id} | {safe(pharmacy.name)} | {safe(pharmacy.phone_number)} | {safe(pharmacy.responsible_person)}"
        for pharmacy in pharmacies
    )
    await message.answer(text, reply_markup=pharmacies_menu())

