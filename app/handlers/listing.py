"""Sahifalangan ro'yxatlar uchun umumiy navigatsiya + qidiruv handlerlari.

- ``lst:{key}:{page}``  — sahifaga o'tish (⬅️/➡️)
- ``lst:{key}:s``       — nom bo'yicha qidiruv (matn so'raladi)
- ``lst:{key}:c``       — qidiruvni tozalash
- ``doc_info:{id}`` / ``ph_info:{id}`` — ro'yxatdan doktor/dorixona detali (karta)

Element tanlash (sale_ph, wh_ph, ball_to_doc, ...) — o'z bo'limlaridagi mavjud
handlerlar bilan ishlanadi; bu router faqat navigatsiya/qidiruv/karta bilan.
"""
from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role
from app.db.repositories import (
    get_doctor_full,
    get_lpu_full,
    get_pharmacy_full,
    get_user_full,
    list_pharmacy_stock,
)
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import role_label, t
from app.keyboards.reply import user_manage_keyboard
from app.services.listing import get_spec, show_list
from app.services.security import (
    can_edit_doctors,
    can_manage_lpu,
    can_view_directories,
    can_view_pharmacies,
    doctor_visible_to,
    pharmacy_visible_to,
)

router = Router(name="listing")


class ListSearch(StatesGroup):
    query = State()


def _entity_in_scope(user, entity, *, operator_ok: bool = False) -> bool:
    """Doktor kartasi uchun ko'lam: markaziy `doctor_visible_to` bilan bir xil
    (regional/medvakil => faqat o'zi yaratgan)."""
    if entity is None or entity.approval_status != ApprovalStatus.APPROVED:
        return False
    if operator_ok and user.role == Role.OPERATOR:
        return True
    return doctor_visible_to(user, entity)


@router.callback_query(F.data.startswith("lst:"))
async def list_nav(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    parts = (callback.data or "").split(":")  # lst:{key}:{arg}
    if len(parts) != 3:
        await callback.answer()
        return
    key, arg = parts[1], parts[2]
    spec = get_spec(key)
    if spec is None:
        await callback.answer()
        return

    data = await state.get_data()
    meta = (data.get("_lists") or {}).get(key) or {}
    ctx = meta.get("ctx") or {}
    query = meta.get("query")

    if arg == "s":  # qidiruv boshlanadi
        await state.update_data(_lst_active=key)
        await state.set_state(ListSearch.query)
        await callback.message.answer(t(lang, "list_search_prompt"))
        await callback.answer()
        return
    if arg == "c":  # qidiruvni tozalash
        await callback.answer()
        await show_list(callback.message, session, user, lang, state, key, ctx=ctx, page=0, query=None, edit=True)
        return
    try:
        page = int(arg)
    except ValueError:
        await callback.answer()
        return
    await callback.answer()
    await show_list(callback.message, session, user, lang, state, key, ctx=ctx, page=page, query=query, edit=True)


@router.message(ListSearch.query)
async def list_search_submit(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        await state.set_state(None)
        return
    query = (message.text or "").strip() or None
    data = await state.get_data()
    key = data.get("_lst_active")
    await state.set_state(None)  # qidiruv holatidan chiqamiz (flow ma'lumotini saqlaymiz)
    if not key or get_spec(key) is None:
        return
    meta = (data.get("_lists") or {}).get(key) or {}
    await show_list(
        message, session, user, lang, state, key, ctx=meta.get("ctx") or {}, page=0, query=query, edit=False
    )


# ==================== Ro'yxatdan detail karta (ko'rish) ====================


@router.callback_query(F.data.startswith("doc_info:"))
async def doctor_card(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_directories(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    doctor = await get_doctor_full(session, int((callback.data or "doc_info:0").split(":", 1)[1]))
    if not _entity_in_scope(user, doctor):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    bu = doctor.bot_user
    tg = bu.telegram_id if bu and bu.telegram_id else "—"
    username = f"@{escape(bu.username)}" if bu and bu.username else "—"
    kb = None
    if can_edit_doctors(user.role):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "btn_doctor_edit"), callback_data=f"doc_edit:{doctor.id}")]
            ]
        )
    await callback.message.answer(
        t(
            lang, "doctor_card",
            id=doctor.id, name=escape(doctor.full_name), phone=safe(doctor.phone_number),
            tg=tg, username=username,
            region=safe(doctor.region.name if doctor.region else None),
            lpu=safe(doctor.lpu.name if doctor.lpu else None),
            category=safe(doctor.class_category), location=safe(doctor.location_text),
            manager=safe(doctor.manager.full_name if doctor.manager else None),
            ball=int(doctor.ball_balance or 0),
        ),
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("ph_info:"))
async def pharmacy_card(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_pharmacies(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    pharmacy = await get_pharmacy_full(session, int((callback.data or "ph_info:0").split(":", 1)[1]))
    if pharmacy is None or pharmacy.approval_status != ApprovalStatus.APPROVED or not pharmacy_visible_to(user, pharmacy):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_pharmacy_stock"), callback_data=f"ph_stock:{pharmacy.id}")]
        ]
    )
    await callback.message.answer(
        t(
            lang, "pharmacy_card",
            id=pharmacy.id, name=escape(pharmacy.name), filial=safe(pharmacy.filial),
            inn=safe(pharmacy.inn), phone=safe(pharmacy.phone_number),
            region=safe(pharmacy.region.name if pharmacy.region else None),
            responsible=safe(pharmacy.responsible_person), location=safe(pharmacy.location_text),
        ),
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("ph_stock:"))
async def pharmacy_stock_view(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_pharmacies(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    pharmacy = await get_pharmacy_full(session, int((callback.data or "ph_stock:0").split(":", 1)[1]))
    if pharmacy is None or (
        pharmacy.approval_status != ApprovalStatus.APPROVED or not pharmacy_visible_to(user, pharmacy)
    ):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    stock = await list_pharmacy_stock(session, pharmacy.id)
    header = t(lang, "pharmacy_stock_header", name=escape(pharmacy.name))
    if not stock:
        await callback.message.answer(header + "\n\n" + t(lang, "pharmacy_stock_empty"))
        return
    rows = "\n".join(
        t(lang, "pharmacy_stock_row", name=escape(d.name), qty=getattr(d, "_pharmacy_qty", 0)) for d in stock
    )
    await callback.message.answer(header + "\n\n" + rows)


@router.callback_query(F.data.startswith("user_info:"))
async def user_card(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if user.role != Role.OWNER:  # foydalanuvchilar ro'yxati faqat owner uchun
        await callback.answer(t(lang, "users_list_closed"), show_alert=True)
        return
    target = await get_user_full(session, int((callback.data or "user_info:0").split(":", 1)[1]))
    if target is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    active = t(lang, "user_active") if target.is_active else t(lang, "user_inactive")
    # Owner o'z hisobini boshqara olmaydi — tugmalar faqat boshqa xodimlarga.
    markup = None if target.id == user.id else user_manage_keyboard(lang, target.id, target.is_active)
    await callback.message.answer(
        t(
            lang, "user_card",
            id=target.id, name=escape(target.full_name), role=role_label(lang, target.role),
            region=safe(target.region.name if target.region else None),
            phone=safe(target.phone_number),
            tg=target.telegram_id if target.telegram_id is not None else "—",
            ball=int(target.ball_balance or 0), active=active,
        ),
        reply_markup=markup,
    )


@router.callback_query(F.data.startswith("lpu_info:"))
async def lpu_card(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_manage_lpu(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    lpu = await get_lpu_full(session, int((callback.data or "lpu_info:0").split(":", 1)[1]))
    # Region-scope: regional/medvakil faqat o'z regioni ЛПУсини ko'radi.
    if lpu is None or (
        user.role in {Role.REGIONAL_MANAGER, Role.MANAGER} and lpu.region_id != user.region_id
    ):
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        t(
            lang, "lpu_card",
            id=lpu.id, name=escape(lpu.name),
            region=safe(lpu.region.name if lpu.region else None),
            address=safe(lpu.address), phone=safe(lpu.phone_number),
        )
    )
