from __future__ import annotations

"""Doktorga bot yuborgan HAR QANDAY xabarni belgilangan muddatda o'chirishga rejalaydi.

aiogram session-middleware: barcha chiquvchi API chaqiruvlarini ushlaydi. Agar
natija Message bo'lsa va chat DOCTOR-rolli foydalanuvchiga tegishli bo'lsa,
`schedule_deletion` orqali 6 soatga o'chirish rejalanadi (deletion_sweeper o'chiradi).

Doktor telegram_id'lari xotirada keshlanadi (har 5 daqiqada yangilanadi) — har
xabar uchun DB so'rovi bo'lmasin.
"""

import logging
import time
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select

from app.db.models import Role, User
from app.db.repositories import schedule_deletion
from app.db.session import AsyncSessionLocal
from app.services.notify import DOCTOR_MESSAGE_TTL

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300.0


class DoctorAutoDeleteMiddleware:
    """Session-middleware: doktor chatiga yuborilgan xabarlarni avto-o'chirishga rejalaydi."""

    def __init__(self) -> None:
        self._doctor_tgs: set[int] = set()
        self._loaded_at: float = 0.0

    async def _doctor_tg_ids(self) -> set[int]:
        now = time.monotonic()
        if not self._loaded_at or (now - self._loaded_at) > _CACHE_TTL_SECONDS:
            try:
                async with AsyncSessionLocal() as session:
                    rows = await session.execute(
                        select(User.telegram_id).where(
                            User.role == Role.DOCTOR, User.telegram_id.is_not(None)
                        )
                    )
                    self._doctor_tgs = {tg for (tg,) in rows.all() if tg is not None}
                self._loaded_at = now
            except Exception:
                logger.debug("doctor tg cache refresh failed", exc_info=True)
        return self._doctor_tgs

    async def __call__(self, make_request, bot: Bot, method):
        result = await make_request(bot, method)
        try:
            if isinstance(result, Message) and result.chat is not None:
                chat_id = result.chat.id
                if chat_id in await self._doctor_tg_ids():
                    async with AsyncSessionLocal() as session:
                        await schedule_deletion(
                            session,
                            chat_id=chat_id,
                            message_id=result.message_id,
                            delete_at=datetime.now(timezone.utc) + DOCTOR_MESSAGE_TTL,
                        )
                        await session.commit()
        except Exception:
            logger.debug("doctor autodelete schedule skipped", exc_info=True)
        return result
