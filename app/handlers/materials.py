from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_material, get_material
from app.handlers.utils import require_callback_user, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import materials_menu
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import can_upload_materials, can_view_materials

router = Router(name="materials")


class MaterialFlow(StatesGroup):
    document = State()
    title = State()


@router.message(F.text.in_(variants("btn_material_upload")))
async def material_upload_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_upload_materials(user.role):
        await message.answer(t(lang, "no_perm_material_upload"))
        return
    await state.set_state(MaterialFlow.document)
    await message.answer(t(lang, "material_upload_prompt"))


@router.message(MaterialFlow.document, F.document)
async def material_document(message: Message, state: FSMContext, lang: str) -> None:
    if message.document is None:
        return
    await state.update_data(file_id=message.document.file_id, file_name=message.document.file_name)
    await state.set_state(MaterialFlow.title)
    await message.answer(t(lang, "material_ask_title"))


@router.message(MaterialFlow.document)
async def material_not_document(message: Message, lang: str) -> None:
    await message.answer(t(lang, "material_not_document"))


@router.message(MaterialFlow.title)
async def material_title(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer(t(lang, "name_too_short"))
        return
    data = await state.get_data()
    material = await add_material(
        session,
        title=title,
        file_id=data["file_id"],
        file_name=data.get("file_name"),
        uploaded_by=user,
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=t(lang, "material_saved", id=material.id, title=safe(material.title)),
        lang=lang,
        reply_markup=materials_menu(lang),
    )


@router.message(F.text.in_(variants("btn_materials")))
async def materials_list(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_materials(user.role):
        await message.answer(t(lang, "section_closed"))
        return
    await show_list(message, session, user, lang, state, "material")


@router.callback_query(F.data.startswith("material:"))
async def material_download(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_materials(user.role):
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    material_id = int(callback.data.split(":", 1)[1]) if callback.data else 0
    material = await get_material(session, material_id)
    if material is None or not material.is_active:
        await callback.answer(t(lang, "material_not_found"), show_alert=True)
        return
    await callback.answer()
    await callback.message.answer_document(document=material.file_id, caption=safe(material.title))
