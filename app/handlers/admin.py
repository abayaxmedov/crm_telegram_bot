from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Role
from app.db.repositories import create_invited_user, list_users
from app.handlers.utils import require_callback_user, require_user, user_line
from app.keyboards.reply import BTN_ADMIN, admin_menu, back_menu, role_inline_keyboard
from app.services.media import answer_media
from app.services.security import ROLE_LABELS, can_create_role
from app.texts import ADMIN_TEXT

router = Router(name="admin")


class CreateUserFlow(StatesGroup):
    full_name = State()


@router.message(F.text == BTN_ADMIN)
async def admin_panel(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role not in {Role.OWNER, Role.MANAGER}:
        await message.answer("Bu bo'lim sizga ochilmagan.")
        return
    await answer_media(message, screen="admin", text=ADMIN_TEXT, reply_markup=admin_menu())


@router.message(F.text == "➕ User yaratish")
async def create_user_start(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role not in {Role.OWNER, Role.MANAGER}:
        await message.answer("User yaratish uchun ruxsat yo'q.")
        return
    await message.answer("Yangi user roleni tanlang:", reply_markup=role_inline_keyboard(user.role))


@router.callback_query(F.data.startswith("create_role:"))
async def create_user_role(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return

    raw_role = callback.data.split(":", 1)[1] if callback.data else ""
    role = Role(raw_role)
    if not can_create_role(user.role, role):
        await callback.answer("Bu roleni yaratishga ruxsat yo'q.", show_alert=True)
        return

    await state.update_data(role=role.value)
    await state.set_state(CreateUserFlow.full_name)
    await callback.message.answer(f"{ROLE_LABELS[role]} uchun ism-familiyani kiriting:", reply_markup=back_menu())
    await callback.answer()


@router.message(CreateUserFlow.full_name)
async def create_user_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    actor = await require_user(message, session)
    if actor is None:
        return

    full_name = (message.text or "").strip()
    if len(full_name) < 3:
        await message.answer("Ism-familiya kamida 3 ta belgidan iborat bo'lsin.")
        return

    data = await state.get_data()
    role = Role(data["role"])
    if not can_create_role(actor.role, role):
        await message.answer("Bu roleni yaratishga ruxsat yo'q.")
        await state.clear()
        return

    invited = await create_invited_user(
        session,
        role=role,
        full_name=full_name,
        phone_number=None,
        created_by=actor,
    )
    await session.commit()
    await state.clear()

    bot_username = settings.bot_username
    if not bot_username:
        me = await message.bot.get_me()
        bot_username = me.username

    invite_link = f"https://t.me/{bot_username}?start={invited.invite_token}" if bot_username else invited.invite_token
    text = (
        "<b>Invite tayyor.</b>\n\n"
        f"<b>User:</b> {escape(invited.full_name)}\n"
        f"<b>Role:</b> {ROLE_LABELS[invited.role]}\n"
        f"<b>Link:</b> {invite_link}\n\n"
        "User shu link orqali kirganda Telegram ID bazaga biriktiriladi va telefon raqami o'zidan so'raladi."
    )
    await answer_media(message, screen="done", text=text, reply_markup=admin_menu())


@router.message(F.text == "👥 Userlar")
async def users_list(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role not in {Role.OWNER, Role.MANAGER}:
        await message.answer("Userlar ro'yxati sizga ochilmagan.")
        return

    rows = await list_users(session)
    if not rows:
        await message.answer("Hali userlar yo'q.", reply_markup=admin_menu())
        return

    text = "<b>Oxirgi userlar</b>\n\n" + "\n".join(user_line(row) for row in rows)
    await message.answer(text, reply_markup=admin_menu())
