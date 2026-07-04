from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db.repositories import seed_owners
from app.db.session import AsyncSessionLocal, init_db
from app.handlers import setup_routers
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.language import LanguageMiddleware
from app.services.profile import setup_bot_profile


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings.validate()

    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_owners(session, settings.owner_ids)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())
    setup_routers(dp)

    await setup_bot_profile(bot)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())

