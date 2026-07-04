from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser

from app.db.repositories import get_user_by_telegram_id
from app.i18n import DEFAULT_LANGUAGE, normalize


class LanguageMiddleware(BaseMiddleware):
    """Har bir message/callback uchun foydalanuvchi tilini aniqlab, `lang` ni
    handler argumentlariga qo'shadi. Til hali tanlanmagan bo'lsa default ishlaydi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        lang = DEFAULT_LANGUAGE
        db_user = None
        session = data.get("session")
        tg_user: TgUser | None = data.get("event_from_user")

        if session is not None and tg_user is not None:
            db_user = await get_user_by_telegram_id(session, tg_user.id)
            if db_user is not None and db_user.language:
                lang = normalize(db_user.language)

        data["db_user"] = db_user
        data["lang"] = lang
        return await handler(event, data)
