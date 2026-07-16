from __future__ import annotations

"""Оптомлар (ulgurji yetkazib beruvchilar) bo'limi — faqat OWNER.

Optom yaratiladi (nom -> ИНН -> telefon) va ro'yxat sahifalangan holda ko'rinadi.
Medvakil «Оптомдан приход» kiritishda shu ro'yxatdan tanlaydi."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_wholesaler, get_wholesaler
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import wholesalers_menu
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import can_manage_wholesalers

router = Router(name="wholesalers")


class WholesalerFlow(StatesGroup):
    name = State()
    inn = State()
    phone = State()


@router.message(F.text.in_(variants("btn_wholesalers")))
async def wholesalers_panel(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_wholesalers(user.role):
        await message.answer(t(lang, "no_perm_wholesalers"))
        return
    await state.clear()
    await answer_media(
        message, screen="admin", text=t(lang, "wholesalers_text"), lang=lang,
        reply_markup=wholesalers_menu(lang),
    )


@router.message(F.text.in_(variants("btn_wholesaler_list")))
async def wholesalers_list(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_wholesalers(user.role):
        await message.answer(t(lang, "no_perm_wholesalers"))
        return
    await show_list(message, session, user, lang, state, "wholesaler")


@router.message(F.text.in_(variants("btn_wholesaler_add")))
async def wholesaler_add_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_wholesalers(user.role):
        await message.answer(t(lang, "no_perm_wholesalers"))
        return
    await state.set_state(WholesalerFlow.name)
    await message.answer(t(lang, "enter_wholesaler_name"))


@router.message(WholesalerFlow.name)
async def wholesaler_name(message: Message, state: FSMContext, lang: str) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer(t(lang, "name_too_short"))
        return
    await state.update_data(name=name)
    await state.set_state(WholesalerFlow.inn)
    await message.answer(t(lang, "enter_wholesaler_inn"))


@router.message(WholesalerFlow.inn)
async def wholesaler_inn(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(inn=clean_optional(message.text))
    await state.set_state(WholesalerFlow.phone)
    await message.answer(t(lang, "enter_wholesaler_phone"))


@router.message(WholesalerFlow.phone)
async def wholesaler_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_wholesalers(user.role):
        await state.clear()
        return
    data = await state.get_data()
    wholesaler = await add_wholesaler(
        session,
        name=data["name"],
        inn=data.get("inn"),
        phone_number=clean_optional(message.text),
        actor=user,
    )
    await session.commit()
    await state.clear()
    await message.answer(
        t(
            lang,
            "wholesaler_saved",
            id=wholesaler.id,
            name=safe(wholesaler.name),
            inn=safe(wholesaler.inn),
            phone=safe(wholesaler.phone_number),
        ),
        reply_markup=wholesalers_menu(lang),
    )


@router.callback_query(F.data.startswith("wholesaler_info:"))
async def wholesaler_card(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    """Ro'yxatdagi ID tugmasi — optom kartasi."""
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_manage_wholesalers(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    wholesaler = await get_wholesaler(session, int((callback.data or "wholesaler_info:0").split(":", 1)[1]))
    if wholesaler is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        t(
            lang, "wholesaler_card",
            id=wholesaler.id, name=safe(wholesaler.name),
            inn=safe(wholesaler.inn), phone=safe(wholesaler.phone_number),
        )
    )
