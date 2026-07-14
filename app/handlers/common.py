from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, User
from app.db.repositories import (
    bind_invited_user,
    get_user_by_invite_token,
    get_user_by_telegram_id,
    try_link_doctor_user,
)
from app.i18n import LANGUAGES, normalize, role_label, t, variants
from app.keyboards.reply import language_inline_keyboard, main_menu, phone_number_keyboard
from app.services.media import answer_media

router = Router(name="common")


class PhoneNumberFlow(StatesGroup):
    phone_number = State()


def _region_line(lang: str, user: User) -> str:
    """Regional menejer / medvakil uchun region qatori (aks holda bo'sh)."""
    if user.role in {Role.REGIONAL_MANAGER, Role.MANAGER}:
        region = user.region.name if user.region else t(lang, "region_unset")
        return f"\n<b>{t(lang, 'your_region')}:</b> {escape(region)}"
    return ""


def _welcome_with_role(lang: str, user: User) -> str:
    return (
        f"{t(lang, 'greeting_hello')}, <b>{escape(user.full_name)}</b>!\n\n"
        f"{t(lang, 'welcome_text')}\n\n"
        f"<b>{t(lang, 'your_role')}:</b> {role_label(lang, user.role)}"
        f"{_region_line(lang, user)}"
    )


async def _show_language_picker(message: Message) -> None:
    await message.answer(t(normalize(None), "choose_language"), reply_markup=language_inline_keyboard())


@router.message(CommandStart())
async def cmd_start(
    message: Message, command: CommandObject, session: AsyncSession, state: FSMContext, lang: str
) -> None:
    if message.from_user is None:
        return

    current_user = await get_user_by_telegram_id(session, message.from_user.id)
    if current_user and current_user.is_active:
        # Har start'da username'ni yangilab turamiz (Telegram'da o'zgargan bo'lishi mumkin;
        # doktorlar ro'yxatida ko'rsatiladi).
        if message.from_user.username != current_user.username:
            current_user.username = message.from_user.username
            await session.commit()
        # Til hali tanlanmagan bo'lsa avval tilni so'raymiz.
        if not current_user.language:
            await _show_language_picker(message)
            return

        lang = normalize(current_user.language)
        if phone_number_required(current_user):
            await state.set_state(PhoneNumberFlow.phone_number)
            await answer_media(
                message,
                screen="welcome",
                text=f"{_welcome_with_role(lang, current_user)}\n\n{t(lang, 'continue_send_phone')}",
                lang=lang,
                reply_markup=phone_number_keyboard(lang),
            )
            return

        await answer_media(
            message,
            screen="welcome",
            text=_welcome_with_role(lang, current_user),
            lang=lang,
            reply_markup=main_menu(current_user.role, lang),
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

    # Yangi foydalanuvchi: avval tilni tanlaydi, keyin telefon so'raladi.
    await _show_language_picker(message)


@router.callback_query(F.data.startswith("set_lang:"))
async def set_language(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return

    code = callback.data.split(":", 1)[1]
    if code not in LANGUAGES:
        await callback.answer()
        return

    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if user is None or not user.is_active:
        await callback.answer()
        return

    user.language = code
    await session.commit()
    lang = code

    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t(lang, "language_set"))

    if phone_number_required(user):
        await state.set_state(PhoneNumberFlow.phone_number)
        await answer_media(
            callback.message,
            screen="welcome",
            text=f"{_welcome_with_role(lang, user)}\n\n{t(lang, 'continue_send_phone')}",
            lang=lang,
            reply_markup=phone_number_keyboard(lang),
        )
        return

    await answer_media(
        callback.message,
        screen="welcome",
        text=_welcome_with_role(lang, user),
        lang=lang,
        reply_markup=main_menu(user.role, lang),
    )


@router.message(Command("language"))
@router.message(F.text.in_(variants("btn_language")))
async def change_language(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    await _show_language_picker(message)


@router.message(PhoneNumberFlow.phone_number, F.contact)
async def phone_from_contact(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if message.from_user is None or message.contact is None:
        return

    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer(t(lang, "phone_own_contact"))
        return

    await save_user_phone(message, session, state, message.contact.phone_number, lang)


@router.message(PhoneNumberFlow.phone_number)
async def phone_from_text(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    phone_number = (message.text or "").strip()
    if len(phone_number) < 7:
        await message.answer(t(lang, "phone_too_short"))
        return

    await save_user_phone(message, session, state, phone_number, lang)


@router.message(Command("menu"))
@router.message(F.text.in_(variants("btn_menu")))
async def cmd_menu(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if not user.language:
        await _show_language_picker(message)
        return
    if phone_number_required(user):
        await request_phone_number(message, lang, state)
        return

    await answer_media(
        message, screen="menu", text=t(lang, "menu_text"), lang=lang, reply_markup=main_menu(user.role, lang), sticker=False
    )


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if phone_number_required(user):
        await request_phone_number(message, lang, state)
        return

    await message.answer(t(lang, "help_text"), reply_markup=main_menu(user.role, lang))


@router.message(Command("id"))
async def cmd_id(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if message.from_user is None:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if phone_number_required(user):
        await request_phone_number(message, lang, state)
        return
    await message.answer(f"<b>{t(lang, 'tg_id')}:</b> <code>{message.from_user.id}</code>")


@router.message()
async def fallback(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return
    if not user.language:
        await _show_language_picker(message)
        return
    if phone_number_required(user):
        await request_phone_number(message, lang, state)
        return

    await message.answer(t(lang, "fallback"), reply_markup=main_menu(user.role, lang))


def phone_number_required(user: User) -> bool:
    return user.role != Role.OWNER and not user.phone_number


async def request_phone_number(message: Message, lang: str, state: FSMContext | None = None) -> None:
    if state is not None:
        await state.set_state(PhoneNumberFlow.phone_number)
    await message.answer(t(lang, "continue_send_phone"), reply_markup=phone_number_keyboard(lang))


async def save_user_phone(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    phone_number: str,
    lang: str,
) -> None:
    if message.from_user is None:
        return

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return

    user.phone_number = phone_number.strip()
    # DOCTOR bo'lsa — telefon orqali doktor yozuviga bog'laymiz (ball olishi uchun).
    if user.role == Role.DOCTOR:
        await try_link_doctor_user(session, user)
    await session.commit()
    await state.clear()

    text = (
        f"{t(lang, 'phone_saved')}\n\n"
        f"<b>{t(lang, 'your_role')}:</b> {role_label(lang, user.role)}"
        f"{_region_line(lang, user)}"
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await answer_media(
        message, screen="menu", text=t(lang, "menu_text"), lang=lang, reply_markup=main_menu(user.role, lang), sticker=False
    )
