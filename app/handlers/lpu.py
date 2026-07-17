from __future__ import annotations

"""ЛПУ (Davolash-profilaktika muassasasi) bo'limi — regional menejer va medvakil.

Bosilганда: ЛПУ ro'yxati (sahifalangan) + ЛПУ yaratish. Yaratilган ЛПУ
yaratuvchining regioniga bog'lanadi; doktor yaratishда doktor shu ЛПУга biriktiriladi."""

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_lpu
from app.handlers.utils import clean_optional, require_user
from app.i18n import t, variants
from app.keyboards.reply import lpu_menu
from app.services.entity_approvals import notify_top_new_lpu
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import can_manage_lpu

router = Router(name="lpu")


class LpuFlow(StatesGroup):
    name = State()
    address = State()  # oxirgi bosqich — telefon so'ralmaydi


@router.message(F.text.in_(variants("btn_lpu")))
async def lpu_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_lpu(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await answer_media(
        message,
        screen="lpu",
        text=t(lang, "lpu_text"),
        lang=lang,
        reply_markup=lpu_menu(lang, can_add=can_manage_lpu(user.role)),
    )


@router.message(F.text.in_(variants("btn_lpu_list")))
async def lpu_list(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_lpu(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await show_list(message, session, user, lang, state, "lpu")


@router.message(F.text.in_(variants("btn_lpu_add")))
async def lpu_add_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_lpu(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await state.set_state(LpuFlow.name)
    await message.answer(t(lang, "enter_lpu_name"))


@router.message(LpuFlow.name)
async def lpu_name(message: Message, state: FSMContext, lang: str) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer(t(lang, "lpu_name_too_short"))
        return
    await state.update_data(name=name)
    await state.set_state(LpuFlow.address)
    await message.answer(t(lang, "enter_lpu_address"))


@router.message(LpuFlow.address)
async def lpu_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        await state.clear()
        return
    if not can_manage_lpu(user.role):
        await state.clear()
        return
    data = await state.get_data()
    lpu = await add_lpu(
        session,
        name=data["name"],
        address=clean_optional(message.text),
        creator=user,
        region_id=user.region_id,
    )
    await session.commit()
    after = data.get("_after")
    await state.clear()
    saved_text = t(lang, "lpu_saved_pending", id=lpu.id, name=escape(lpu.name))
    # TOP menejerga REAL-TIME tasdiq so'rovi (maqom — faqat belgi, ЛПУ darrov ishlatiladi).
    await notify_top_new_lpu(message.bot, session, lpu.id)

    if after == "report":
        # Kundalik oqimидан kelgan — menyuга emas, shu yangi ЛПУ doktorlarига o'tamiz
        # (doktor bo'lmasa u yerда «➕ Доктор яратиш» tugmasи chiqadi).
        await message.answer(saved_text)
        await state.update_data(lpu_id=lpu.id)
        await show_list(message, session, user, lang, state, "rep_tgt_doctor", ctx={"lpu_id": lpu.id})
        return

    await answer_media(
        message,
        screen="done",
        text=saved_text,
        lang=lang,
        reply_markup=lpu_menu(lang, can_add=can_manage_lpu(user.role)),
    )
