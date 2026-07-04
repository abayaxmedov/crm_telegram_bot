from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand

from app.i18n import RU, UZ_CYRL, t

logger = logging.getLogger(__name__)


def _commands(lang: str) -> list[BotCommand]:
    return [
        BotCommand(command="start", description=t(lang, "cmd_start")),
        BotCommand(command="menu", description=t(lang, "cmd_menu")),
        BotCommand(command="language", description=t(lang, "cmd_language")),
        BotCommand(command="help", description=t(lang, "cmd_help")),
        BotCommand(command="id", description=t(lang, "cmd_id")),
    ]


async def setup_bot_profile(bot: Bot) -> None:
    try:
        # Default (Ўзбекча кирилл) — tili aniqlanmagan foydalanuvchilar uchun.
        await bot.set_my_commands(_commands(UZ_CYRL))
        await bot.set_my_description(t(UZ_CYRL, "bot_description"))
        await bot.set_my_short_description(t(UZ_CYRL, "bot_short_description"))

        # Rus tilidagi Telegram interfeysi uchun.
        await bot.set_my_commands(_commands(RU), language_code="ru")
        await bot.set_my_description(t(RU, "bot_description"), language_code="ru")
        await bot.set_my_short_description(t(RU, "bot_short_description"), language_code="ru")
    except Exception:
        logger.exception("Bot profile sozlamalarini Telegramga yuborib bo'lmadi")
