from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Role
from app.db.repositories import create_invited_user, get_region, list_regions, list_users
from app.handlers.utils import require_callback_user, require_user, user_line
from app.i18n import role_label, t, variants
from app.keyboards.reply import admin_menu, back_menu, entities_inline, role_inline_keyboard
from app.services.media import answer_media
from app.services.security import ROLES_WITH_REGION, can_create_role

router = Router(name="admin")


class CreateUserFlow(StatesGroup):
    full_name = State()
    region = State()


@router.message(F.text.in_(variants("btn_admin")))
async def admin_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role != Role.OWNER:
        await message.answer(t(lang, "section_closed"))
        return
    await answer_media(message, screen="admin", text=t(lang, "admin_text"), lang=lang, reply_markup=admin_menu(lang))


@router.message(F.text.in_(variants("btn_user_create")))
async def create_user_start(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role != Role.OWNER:
        await message.answer(t(lang, "no_perm_user_create"))
        return
    await message.answer(t(lang, "choose_new_role"), reply_markup=role_inline_keyboard(user.role, lang))


@router.callback_query(F.data.startswith("create_role:"))
async def create_user_role(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return

    raw_role = callback.data.split(":", 1)[1] if callback.data else ""
    role = Role(raw_role)
    if not can_create_role(user.role, role):
        await callback.answer(t(lang, "role_not_allowed"), show_alert=True)
        return

    await state.update_data(role=role.value)
    await state.set_state(CreateUserFlow.full_name)
    await callback.message.answer(
        t(lang, "enter_fullname_for_role", role=role_label(lang, role)), reply_markup=back_menu(lang)
    )
    await callback.answer()


@router.message(CreateUserFlow.full_name)
async def create_user_name(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    actor = await require_user(message, session)
    if actor is None:
        return

    full_name = (message.text or "").strip()
    if len(full_name) < 3:
        await message.answer(t(lang, "fullname_too_short"))
        return

    data = await state.get_data()
    role = Role(data["role"])
    if not can_create_role(actor.role, role):
        await message.answer(t(lang, "role_not_allowed"))
        await state.clear()
        return

    await state.update_data(full_name=full_name)

    # Regional menejer / medvakil uchun region so'raladi.
    if role in ROLES_WITH_REGION:
        regions = await list_regions(session)
        if not regions:
            await message.answer(t(lang, "no_regions_create_first"), reply_markup=admin_menu(lang))
            await state.clear()
            return
        await state.set_state(CreateUserFlow.region)
        await message.answer(
            t(lang, "choose_region"),
            reply_markup=entities_inline([(r.id, r.name) for r in regions], "cu_region"),
        )
        return

    await _finalize_user(message, session, state, actor, lang, region_id=None)


@router.callback_query(CreateUserFlow.region, F.data.startswith("cu_region:"))
async def create_user_region(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    actor = await require_callback_user(callback, session)
    if actor is None:
        return
    region_id = int(callback.data.split(":", 1)[1]) if callback.data else 0
    region = await get_region(session, region_id)
    if region is None:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return
    await callback.answer()
    await _finalize_user(callback.message, session, state, actor, lang, region_id=region_id)


async def _finalize_user(
    message: Message, session: AsyncSession, state: FSMContext, actor, lang: str, *, region_id: int | None
) -> None:
    data = await state.get_data()
    role = Role(data["role"])
    invited = await create_invited_user(
        session,
        role=role,
        full_name=data["full_name"],
        phone_number=None,
        created_by=actor,
        region_id=region_id,
    )
    await session.commit()
    await state.clear()

    bot_username = settings.bot_username
    if not bot_username:
        me = await message.bot.get_me()
        bot_username = me.username

    invite_link = f"https://t.me/{bot_username}?start={invited.invite_token}" if bot_username else invited.invite_token
    text = t(
        lang,
        "invite_ready",
        name=escape(invited.full_name),
        role=role_label(lang, invited.role),
        link=invite_link,
    )
    await answer_media(message, screen="done", text=text, lang=lang, reply_markup=admin_menu(lang))


@router.message(F.text.in_(variants("btn_users")))
async def users_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role != Role.OWNER:
        await message.answer(t(lang, "users_list_closed"))
        return

    rows = await list_users(session)
    if not rows:
        await message.answer(t(lang, "no_users"), reply_markup=admin_menu(lang))
        return

    text = t(lang, "last_users") + "\n\n" + "\n".join(user_line(row, lang) for row in rows)
    await message.answer(text, reply_markup=admin_menu(lang))
