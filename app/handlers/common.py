from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role
from app.db.repositories import bind_invited_user, get_user_by_invite_token, get_user_by_telegram_id
from app.keyboards.reply import BTN_MENU, main_menu, phone_number_keyboard
from app.services.media import answer_media
from app.texts import MENU_TEXT, WELCOME_TEXT

router = Router(name="common")


class PhoneNumberFlow(StatesGroup):
    phone_number = State()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return

    current_user = await get_user_by_telegram_id(session, message.from_user.id)
    if current_user and current_user.is_active:
        if phone_number_required(current_user):
            text = (
                f"{WELCOME_TEXT}\n\n"
                f"<b>Sizning rolingiz:</b> <code>{current_user.role.value}</code>\n\n"
                "Davom etish uchun telefon raqamingizni yuboring."
            )
            await state.set_state(PhoneNumberFlow.phone_number)
            await answer_media(message, screen="welcome", text=text, reply_markup=phone_number_keyboard())
            return

        text = (
            f"{WELCOME_TEXT}\n\n"
            f"<b>Sizning rolingiz:</b> <code>{current_user.role.value}</code>"
        )
        await answer_media(
            message,
            screen="welcome",
            text=text,
            reply_markup=main_menu(current_user.role),
        )
        return

    token = (command.args or "").strip()
    if not token:
        return

    invited_user = await get_user_by_invite_token(session, token)
    if invited_user is None or invited_user.invite_used or not invited_user.is_active:
        return

    if invited_user.telegram_id and invited_user.telegram_id != message.from_user.id:
        return

    display_name = message.from_user.full_name or f"User {message.from_user.id}"
    await bind_invited_user(
        session,
        user=invited_user,
        telegram_id=message.from_user.id,
        full_name=display_name,
        username=message.from_user.username,
    )
    await session.commit()

    text = (
        f"{WELCOME_TEXT}\n\n"
        f"<b>Profil:</b> {escape(invited_user.full_name)}\n"
        f"<b>Sizning rolingiz:</b> <code>{invited_user.role.value}</code>\n\n"
        "Davom etish uchun telefon raqamingizni yuboring."
    )
    await state.set_state(PhoneNumberFlow.phone_number)
    await answer_media(message, screen="welcome", text=text, reply_markup=phone_number_keyboard())


@router.message(PhoneNumberFlow.phone_number, F.contact)
async def phone_from_contact(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None or message.contact is None:
        return

    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Iltimos, o'zingizning Telegram contactingizni yuboring.")
        return

    await save_user_phone(message, session, state, message.contact.phone_number)


@router.message(PhoneNumberFlow.phone_number)
async def phone_from_text(message: Message, session: AsyncSession, state: FSMContext) -> None:
    phone_number = (message.text or "").strip()
    if len(phone_number) < 7:
        await message.answer("Telefon raqam juda qisqa. Masalan: +998901234567")
        return

    await save_user_phone(message, session, state, phone_number)


@router.message(Command("menu"))
@router.message(F.text == BTN_MENU)
async def cmd_menu(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if phone_number_required(user):
        await request_phone_number(message, state)
        return

    await answer_media(message, screen="menu", text=MENU_TEXT, reply_markup=main_menu(user.role), sticker=False)


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if phone_number_required(user):
        await request_phone_number(message, state)
        return

    text = (
        "<b>Yordam</b>\n\n"
        "Bot yopiq CRM sifatida ishlaydi. Barcha bo'limlar role bo'yicha ochiladi.\n"
        "Muammo bo'lsa ownerga murojaat qiling yoki /id orqali Telegram ID ni yuboring."
    )
    await message.answer(text, reply_markup=main_menu(user.role))


@router.message(Command("id"))
async def cmd_id(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if phone_number_required(user):
        await request_phone_number(message, state)
        return
    await message.answer(f"<b>Telegram ID:</b> <code>{message.from_user.id}</code>")


@router.message()
async def fallback(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if phone_number_required(user):
        await request_phone_number(message, state)
        return

    await message.answer("Bo'limni menyudan tanlang yoki /menu buyrug'ini yuboring.", reply_markup=main_menu(user.role))


def phone_number_required(user) -> bool:
    return user.role != Role.OWNER and not user.phone_number


async def request_phone_number(message: Message, state: FSMContext | None = None) -> None:
    if state is not None:
        await state.set_state(PhoneNumberFlow.phone_number)
    await message.answer(
        "Davom etish uchun telefon raqamingizni yuboring.",
        reply_markup=phone_number_keyboard(),
    )


async def save_user_phone(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    phone_number: str,
) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return

    user.phone_number = phone_number.strip()
    await session.commit()
    await state.clear()

    text = (
        "<b>Telefon raqamingiz saqlandi.</b>\n\n"
        f"<b>Sizning rolingiz:</b> <code>{user.role.value}</code>"
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await answer_media(message, screen="menu", text=MENU_TEXT, reply_markup=main_menu(user.role), sticker=False)
