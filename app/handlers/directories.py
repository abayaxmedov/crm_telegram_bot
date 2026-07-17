from __future__ import annotations

from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role, User
from app.db.repositories import (
    add_doctor,
    add_pharmacy,
    edit_doctor,
    get_doctor,
    get_lpu,
    get_region,
    list_doctors_visible,
    list_lpus_in_region,
    list_pharmacies_visible,
    list_regions,
)
from app.handlers.utils import clean_optional, parse_phone, require_callback_user, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import (
    doctor_edit_menu_keyboard,
    doctors_menu,
    entities_inline,
    inline_id_grid,
    location_request_keyboard,
    pharmacies_menu,
)
from app.services.approvals import notify_operators_new_pharmacy
from app.services.excel import build_xlsx
from app.services.entity_approvals import notify_top_new_doctor
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import (
    can_add_directories,
    can_add_doctors,
    can_edit_doctors,
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
    lpu = State()


class DoctorEditFlow(StatesGroup):
    value = State()  # ism/telefon/kategoriya matni (edit_field FSM data'da)


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
        reply_markup=doctors_menu(lang, can_add=can_add_doctors(user.role)),
    )


@router.message(F.text.in_(variants("btn_doctor_add")))
async def doctor_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_add_doctors(user.role):
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
    # Doktor telefoni MAJBURIY va kamida 7 raqam — u doktorni botga bog'lash kaliti.
    phone = parse_phone(message.text)
    if phone is None:
        await message.answer(t(lang, "phone_too_short"))
        return
    await state.update_data(phone=phone)
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
    data = await state.get_data()

    # Kundalik oqimидан kelган: ЛПУ allaqачон tanlanган — qayta so'ramaymиz, darrov yaratamиz.
    if data.get("_after") == "report" and data.get("lpu_id"):
        lpu = await get_lpu(session, data["lpu_id"])
        if lpu is None or (
            user.role in REGION_LOCKED_ROLES and lpu.region_id != user.region_id
        ):
            await state.clear()
            await message.answer(t(lang, "entity_not_found"))
            return
        await _save_doctor(message, session, state, lang, user, region_id=lpu.region_id, lpu_id=lpu.id)
        return

    # Medvakil/regional menejer o'z regioniga biriktirilgan — region so'ralmaydi,
    # to'g'ridan-to'g'ri O'Z regionidagi ЛПУ ro'yxati chiqadi (boshqa region ЛПУлари emas).
    if user.role in REGION_LOCKED_ROLES:
        if user.region_id is None:
            await state.clear()
            await message.answer(t(lang, "no_region_assigned"))
            return
        await _ask_doctor_lpu(message, session, state, lang, user, user.region_id)
        return
    await _ask_region(message, session, state, lang, DoctorFlow.region, "doc_region")


# Regionga biriktirilgan rollar: o'z regionidan boshqa region/ЛПУ ni ko'ra olmaydi.
REGION_LOCKED_ROLES = {Role.MANAGER, Role.REGIONAL_MANAGER}


async def _ask_doctor_lpu(
    message: Message, session: AsyncSession, state: FSMContext, lang: str, user: User, region_id: int
) -> None:
    """Doktor yaratish: shu REGIONDAGI ЛПУ ro'yxatini ko'rsatadi."""
    lpus = await list_lpus_in_region(session, region_id)
    if not lpus:
        # Bu regionda ЛПУ yo'q — avval ЛПУ yaratilishi kerak.
        await state.clear()
        await answer_media(
            message, screen="done", text=t(lang, "doctor_no_lpu_in_region"),
            lang=lang, reply_markup=doctors_menu(lang, can_add=can_add_doctors(user.role)),
        )
        return
    await state.update_data(region_id=region_id)
    await state.set_state(DoctorFlow.lpu)
    rows = "\n".join(f"#{lp.id} | {safe(lp.name)}" for lp in lpus)
    await message.answer(
        t(lang, "doctor_choose_lpu") + "\n\n" + rows,
        reply_markup=inline_id_grid([lp.id for lp in lpus], "doc_lpu"),
    )


@router.callback_query(DoctorFlow.region, F.data.startswith("doc_region:"))
async def doctor_pick_region(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    """Region tanlangach — shu regiondagi ЛПУ ro'yxati so'raladi."""
    user = await require_callback_user(callback, session)
    if user is None:
        return
    region_id = int(callback.data.split(":", 1)[1]) if callback.data else 0
    region = await get_region(session, region_id)
    if region is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    # Soxta callback'ga qarshi: medvakil/regional o'z regionidan boshqasini tanlay olmaydi.
    if user.role in REGION_LOCKED_ROLES and region_id != user.region_id:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    await _ask_doctor_lpu(callback.message, session, state, lang, user, region_id)


async def _save_doctor(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    lang: str,
    user: User,
    *,
    region_id: int | None,
    lpu_id: int,
) -> None:
    """Doktorni yaratadi va oqimni yakunlaydi.

    Maqom PENDING (⏳) — bu TO'SIQ EMAS: doktor darrov ishlatiladi (hisobot yozish),
    faqat SOTUV/BALL/СОВҒА uchun TOP menejer tasdig'i (✅) kerak.

    Kundalikdan kelgan bo'lsa (`_after=report`) — menyuga emas, shu ЛПУ doktorlari
    ro'yxatiga qaytadi, foydalanuvchi yangi doktorni tanlab hisobotni davom ettiradi."""
    data = await state.get_data()
    after = data.get("_after")
    doctor = await add_doctor(
        session,
        full_name=data["full_name"],
        phone_number=data.get("phone"),
        location_text=data.get("location"),
        class_category=data.get("category"),
        manager=user,
        notes=data.get("notes"),
        region_id=region_id,
        lpu_id=lpu_id,
        approval_status=ApprovalStatus.PENDING,
    )
    await session.commit()
    await state.clear()
    saved_text = t(lang, "doctor_saved_pending", id=doctor.id, name=escape(doctor.full_name))
    # TOP menejerga REAL-TIME tasdiq so'rovi (tasdiq — sotuv/ball uchun darvoza).
    await notify_top_new_doctor(message.bot, session, doctor.id)

    if after == "report":
        # Kundalik oqimидан kelgan — menyuга emas, shu ЛПУ doktorlarига qaytamиz;
        # foydalanuвчи yangi doktorни tanlab hisobotни davom ettiradи.
        await message.answer(saved_text)
        await state.update_data(lpu_id=lpu_id)
        await show_list(message, session, user, lang, state, "rep_tgt_doctor", ctx={"lpu_id": lpu_id})
        return

    await answer_media(message, screen="done", text=saved_text, lang=lang, reply_markup=doctors_menu(lang))


@router.callback_query(DoctorFlow.lpu, F.data.startswith("doc_lpu:"))
async def doctor_finish(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    lpu_id = int(callback.data.split(":", 1)[1]) if callback.data else 0
    data = await state.get_data()
    region_id = data.get("region_id")
    lpu = await get_lpu(session, lpu_id)
    # Soxta callback'ga qarshi: ЛПУ tanlangan regionga tegishli bo'lishi shart.
    if lpu is None or lpu.region_id != region_id:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    await _save_doctor(callback.message, session, state, lang, user, region_id=region_id, lpu_id=lpu_id)


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

    # Tasdiq kutilayotgan bo'lsa — operatorlarga REAL-TIME so'rov yuboramiz
    # (operator bo'limni ochmasdan, xabarning o'zidan tasdiqlaydi).
    if status == ApprovalStatus.PENDING:
        await notify_operators_new_pharmacy(message.bot, session, pharmacy.id)

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


# ==================== Doktor ma'lumotlarini tahrirlash (owner/TOP/product) ====================


async def _require_doctor_editor(callback: CallbackQuery, session: AsyncSession, lang: str):
    """can_edit_doctors + nishon doktor mavjudligini tekshiradi. (editor, doctor) qaytaradi."""
    user = await require_callback_user(callback, session)
    if user is None:
        return None, None
    if not can_edit_doctors(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return None, None
    parts = (callback.data or "").split(":")
    doctor = await get_doctor(session, int(parts[1])) if len(parts) >= 2 else None
    if doctor is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return user, None
    return user, doctor


@router.callback_query(F.data.startswith("doc_edit:"))
async def doctor_edit_menu(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    editor, doctor = await _require_doctor_editor(callback, session, lang)
    if editor is None or doctor is None:
        return
    await callback.answer()
    await callback.message.answer(
        t(lang, "de_menu", name=escape(doctor.full_name)),
        reply_markup=doctor_edit_menu_keyboard(lang, doctor.id),
    )


@router.callback_query(F.data.startswith("de_name:"))
async def doctor_edit_name(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    editor, doctor = await _require_doctor_editor(callback, session, lang)
    if editor is None or doctor is None:
        return
    await state.update_data(edit_doc_id=doctor.id, edit_field="name")
    await state.set_state(DoctorEditFlow.value)
    await callback.message.answer(t(lang, "enter_doctor_fullname"))
    await callback.answer()


@router.callback_query(F.data.startswith("de_phone:"))
async def doctor_edit_phone(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    editor, doctor = await _require_doctor_editor(callback, session, lang)
    if editor is None or doctor is None:
        return
    await state.update_data(edit_doc_id=doctor.id, edit_field="phone")
    await state.set_state(DoctorEditFlow.value)
    await callback.message.answer(t(lang, "enter_phone"))
    await callback.answer()


@router.callback_query(F.data.startswith("de_cat:"))
async def doctor_edit_category(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    editor, doctor = await _require_doctor_editor(callback, session, lang)
    if editor is None or doctor is None:
        return
    await state.update_data(edit_doc_id=doctor.id, edit_field="category")
    await state.set_state(DoctorEditFlow.value)
    await callback.message.answer(t(lang, "enter_category"))
    await callback.answer()


@router.message(DoctorEditFlow.value)
async def doctor_edit_value_save(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None or not can_edit_doctors(user.role):
        await state.clear()
        return
    data = await state.get_data()
    doctor = await get_doctor(session, data.get("edit_doc_id"))
    field = data.get("edit_field")
    if doctor is None:
        await state.clear()
        await message.answer(t(lang, "entity_not_found"))
        return
    raw = (message.text or "").strip()
    if field == "name":
        if len(raw) < 3:
            await message.answer(t(lang, "fullname_too_short"))
            return
        await edit_doctor(session, doctor=doctor, actor=user, full_name=raw)
    elif field == "phone":
        phone = parse_phone(raw)
        if phone is None:
            await message.answer(t(lang, "phone_too_short"))
            return
        await edit_doctor(session, doctor=doctor, actor=user, phone_number=phone)
    else:  # category
        await edit_doctor(session, doctor=doctor, actor=user, class_category=clean_optional(raw))
    await session.commit()
    await state.clear()
    await message.answer(
        t(lang, "doctor_edited_ok", name=escape(doctor.full_name)),
        reply_markup=doctors_menu(lang, can_add=can_add_doctors(user.role)),
    )


@router.callback_query(F.data.startswith("de_region:"))
async def doctor_edit_region_start(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    editor, doctor = await _require_doctor_editor(callback, session, lang)
    if editor is None or doctor is None:
        return
    regions = await list_regions(session)
    if not regions:
        await callback.answer(t(lang, "no_regions_create_first"), show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        t(lang, "de_choose_region"),
        reply_markup=entities_inline([(r.id, r.name) for r in regions], f"dereg:{doctor.id}"),
    )


@router.callback_query(F.data.startswith("dereg:"))
async def doctor_edit_region_set(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_edit_doctors(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    parts = (callback.data or "").split(":")  # dereg:{doc}:{region}
    if len(parts) != 3:
        await callback.answer()
        return
    doctor = await get_doctor(session, int(parts[1]))
    region = await get_region(session, int(parts[2]))
    if doctor is None or region is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await edit_doctor(session, doctor=doctor, actor=user, region_id=region.id)
    await session.commit()
    await callback.answer()
    await callback.message.answer(
        t(lang, "doctor_edited_ok", name=escape(doctor.full_name)) + f" — 🌐 {escape(region.name)}"
    )


@router.callback_query(F.data.startswith("de_lpu:"))
async def doctor_edit_lpu_start(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    editor, doctor = await _require_doctor_editor(callback, session, lang)
    if editor is None or doctor is None:
        return
    lpus = await list_lpus_in_region(session, doctor.region_id)
    if not lpus:
        await callback.answer(t(lang, "doctor_no_lpu_in_region"), show_alert=True)
        return
    await callback.answer()
    rows = "\n".join(f"#{lp.id} | {safe(lp.name)}" for lp in lpus)
    await callback.message.answer(
        t(lang, "doctor_choose_lpu") + "\n\n" + rows,
        reply_markup=inline_id_grid([lp.id for lp in lpus], f"delpu:{doctor.id}"),
    )


@router.callback_query(F.data.startswith("delpu:"))
async def doctor_edit_lpu_set(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_edit_doctors(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    parts = (callback.data or "").split(":")  # delpu:{doc}:{lpu}
    if len(parts) != 3:
        await callback.answer()
        return
    doctor = await get_doctor(session, int(parts[1]))
    lpu = await get_lpu(session, int(parts[2]))
    # ЛПУ doktor regioniga tegishli bo'lishi shart.
    if doctor is None or lpu is None or lpu.region_id != doctor.region_id:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await edit_doctor(session, doctor=doctor, actor=user, lpu_id=lpu.id)
    await session.commit()
    await callback.answer()
    await callback.message.answer(
        t(lang, "doctor_edited_ok", name=escape(doctor.full_name)) + f" — 🏥 {escape(lpu.name)}"
    )
