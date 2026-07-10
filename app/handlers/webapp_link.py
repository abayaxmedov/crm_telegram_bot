from __future__ import annotations

"""Analitika web-paneliga kirish havolasi (owner / TOP / product menejer).

Hozircha brauzer havolasi (imzolangan token bilan). HTTPS domen olingach
`WEBAPP_TELEGRAM_URL` env o'rnatilsa Telegram ichida ochiladigan WebApp tugmasi
ham qo'shiladi."""

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.handlers.utils import require_user
from app.i18n import t, variants
from app.services.security import can_use_webapp
from app.webapp.auth import make_token

router = Router(name="webapp_link")


@router.message(F.text.in_(variants("btn_webapp")))
async def webapp_link(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_use_webapp(user.role):
        await message.answer(t(lang, "webapp_no_perm"))
        return

    token = make_token(user.id)
    link = f"{settings.webapp_base_url.rstrip('/')}/?token={token}"

    reply_markup = None
    if settings.webapp_telegram_url:
        # HTTPS domen mavjud — Telegram ichida ochiladigan tugma.
        webapp_url = f"{settings.webapp_telegram_url.rstrip('/')}/?token={token}"
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "btn_webapp_open"), web_app=WebAppInfo(url=webapp_url))]
            ]
        )

    await message.answer(t(lang, "webapp_link_text", link=link), reply_markup=reply_markup)
