from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_region, list_regions
from app.handlers.utils import require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import regions_menu
from app.services.media import answer_media
from app.services.security import can_manage_regions

router = Router(name="regions")


class RegionFlow(StatesGroup):
    name = State()


@router.message(F.text.in_(variants("btn_regions")))
async def regions_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_regions(user.role):
        await message.answer(t(lang, "no_perm_regions"))
        return
    await answer_media(
        message, screen="admin", text=t(lang, "regions_text"), lang=lang, reply_markup=regions_menu(lang)
    )


@router.message(F.text.in_(variants("btn_region_add")))
async def region_add_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_regions(user.role):
        await message.answer(t(lang, "no_perm_regions"))
        return
    await state.set_state(RegionFlow.name)
    await message.answer(t(lang, "enter_region_name"))


@router.message(RegionFlow.name)
async def region_add_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_regions(user.role):
        await state.clear()
        return

    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer(t(lang, "name_too_short"))
        return

    existing = await list_regions(session, only_active=False)
    if any(r.name.lower() == name.lower() for r in existing):
        await message.answer(t(lang, "region_exists"))
        return

    region = await add_region(session, name=name, actor=user)
    await session.commit()
    await state.clear()
    await message.answer(
        t(lang, "region_saved", id=region.id, name=escape(region.name)), reply_markup=regions_menu(lang)
    )


@router.message(F.text.in_(variants("btn_regions_list")))
async def regions_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_regions(user.role):
        await message.answer(t(lang, "no_perm_regions"))
        return
    regions = await list_regions(session, only_active=False)
    if not regions:
        await message.answer(t(lang, "regions_empty"), reply_markup=regions_menu(lang))
        return
    text = t(lang, "regions_header") + "\n\n" + "\n".join(f"#{r.id} | {safe(r.name)}" for r in regions)
    await message.answer(text, reply_markup=regions_menu(lang))
