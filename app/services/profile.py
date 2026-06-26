from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand

from app.texts import BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION

logger = logging.getLogger(__name__)


async def setup_bot_profile(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="menu", description="Asosiy menyu"),
        BotCommand(command="help", description="Yordam"),
        BotCommand(command="id", description="Telegram ID ko'rish"),
    ]

    try:
        await bot.set_my_commands(commands)
        await bot.set_my_description(BOT_DESCRIPTION)
        await bot.set_my_short_description(BOT_SHORT_DESCRIPTION)
    except Exception:
        logger.exception("Bot profile sozlamalarini Telegramga yuborib bo'lmadi")

