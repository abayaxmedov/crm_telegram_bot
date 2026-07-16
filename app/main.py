from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web as aioweb

from app.config import settings
from app.db.repositories import seed_owners
from app.db.session import AsyncSessionLocal, init_db
from app.handlers import setup_routers
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.language import LanguageMiddleware
from app.services.doctor_autodelete import DoctorAutoDeleteMiddleware
from app.services.notify import deletion_sweeper
from app.services.profile import setup_bot_profile
from app.webapp.server import create_webapp


def _build_storage() -> BaseStorage:
    """Redis mavjud bo'lsa FSM holatini unda saqlaymiz (bot restart/deploy'dan omon
    qoladi). Aks holda MemoryStorage — restart'da holat yo'qoladi."""
    if settings.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage

            storage = RedisStorage.from_url(settings.redis_url)
            logging.info("FSM storage: Redis (%s)", settings.redis_url)
            return storage
        except Exception:
            logging.exception("Redis storage ulanmadi — MemoryStorage'ga o'tildi")
    logging.warning("FSM storage: MemoryStorage (restart'da holat yo'qoladi)")
    return MemoryStorage()


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
    # Doktorga yuborilgan har qanday xabar 6 soatda avto-o'chadi.
    bot.session.middleware(DoctorAutoDeleteMiddleware())
    dp = Dispatcher(storage=_build_storage())
    dp.update.middleware(DbSessionMiddleware())
    # OUTER middleware: filtrlardan (RoleFilter) oldin ishlashi uchun, shunda
    # db_user/lang filtrlar uchun ham mavjud bo'ladi.
    dp.message.outer_middleware(LanguageMiddleware())
    dp.callback_query.outer_middleware(LanguageMiddleware())
    setup_routers(dp)

    await setup_bot_profile(bot)

    # Analitika web-paneli (aiohttp) — polling bilan bitta processda.
    runner = aioweb.AppRunner(create_webapp())
    await runner.setup()
    site = aioweb.TCPSite(runner, settings.webapp_host, settings.webapp_port)
    await site.start()
    logging.info("Webapp ishga tushdi: http://%s:%s (%s)", settings.webapp_host, settings.webapp_port, settings.webapp_base_url)

    # Doktor xabarlarini 24 soatdan keyin o'chiruvchi fon vazifasi.
    sweeper_task = asyncio.create_task(deletion_sweeper(bot))

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        sweeper_task.cancel()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
