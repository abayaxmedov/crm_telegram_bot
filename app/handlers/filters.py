from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.db.models import Role, User


class RoleFilter(BaseFilter):
    """Handlerni faqat berilgan rollar uchun ishga tushiradi.

    LanguageMiddleware `data["db_user"]` ni beradi. Rol mos kelmasa filter False
    qaytaradi va update keyingi routerga o'tadi (masalan Медвакил "Финансы" -> rep,
    owner "Финансы" -> eski owner handler)."""

    def __init__(self, *roles: Role) -> None:
        self.roles = set(roles)

    async def __call__(self, event: TelegramObject, db_user: User | None = None) -> bool:
        return db_user is not None and db_user.role in self.roles
