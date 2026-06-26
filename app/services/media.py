from __future__ import annotations

from pathlib import Path

from aiogram.types import FSInputFile, Message, ReplyKeyboardMarkup

from app.config import settings
from app.texts import PHOTO_BY_SCREEN, SCREEN_TITLES, STICKER_BY_SCREEN


async def answer_media(
    message: Message,
    *,
    screen: str,
    text: str,
    reply_markup: ReplyKeyboardMarkup | None = None,
    sticker: bool = True,
) -> None:
    if sticker:
        sticker_path = _asset_path("stickers", STICKER_BY_SCREEN.get(screen))
        if sticker_path:
            await message.answer_sticker(FSInputFile(sticker_path))

    photo_path = _asset_path("photos", PHOTO_BY_SCREEN.get(screen))
    if photo_path:
        if len(text) <= 1000:
            await message.answer_photo(FSInputFile(photo_path), caption=text, reply_markup=reply_markup)
            return

        await message.answer_photo(FSInputFile(photo_path), caption=f"<b>{SCREEN_TITLES.get(screen, 'CRM')}</b>")

    await message.answer(text, reply_markup=reply_markup)


def _asset_path(folder: str, filename: str | None) -> Path | None:
    if not filename:
        return None
    path = settings.assets_dir / folder / filename
    return path if path.exists() else None

