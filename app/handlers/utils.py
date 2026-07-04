from __future__ import annotations

from html import escape

from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import get_user_by_telegram_id
from app.i18n import role_label, t


async def require_user(message: Message, session: AsyncSession) -> User | None:
    if message.from_user is None:
        return None

    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        return None
    return user


async def require_callback_user(callback: CallbackQuery, session: AsyncSession) -> User | None:
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if user is None or not user.is_active:
        await callback.answer()
        return None
    return user


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if value in {"", "-", "yo'q", "yo‘q", "йўқ", "нет", "no"}:
        return None
    return value


def safe(value: object | None) -> str:
    return escape(str(value)) if value is not None else "-"


def user_line(user: User, lang: str) -> str:
    tg = user.telegram_id if user.telegram_id is not None else t(lang, "invite_pending")
    active = t(lang, "user_active") if user.is_active else t(lang, "user_inactive")
    return f"#{user.id} | {safe(user.full_name)} | {role_label(lang, user.role)} | {tg} | {active}"
