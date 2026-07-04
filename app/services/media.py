from __future__ import annotations

from pathlib import Path

from aiogram.types import FSInputFile, Message, ReplyKeyboardMarkup

from app.config import settings
from app.i18n import DEFAULT_LANGUAGE, normalize, t
from app.texts import PHOTO_BY_SCREEN, SCREEN_TITLE_KEYS, STICKER_BY_SCREEN


async def answer_media(
    message: Message,
    *,
    screen: str,
    text: str,
    lang: str,
    reply_markup: ReplyKeyboardMarkup | None = None,
    sticker: bool = True,
) -> None:
    if sticker:
        sticker_path = _asset_path("stickers", STICKER_BY_SCREEN.get(screen), lang)
        if sticker_path:
            await message.answer_sticker(FSInputFile(sticker_path))

    photo_path = _asset_path("photos", PHOTO_BY_SCREEN.get(screen), lang)
    if photo_path:
        if len(text) <= 1000:
            await message.answer_photo(FSInputFile(photo_path), caption=text, reply_markup=reply_markup)
            return

        title_key = SCREEN_TITLE_KEYS.get(screen, "title_menu")
        await message.answer_photo(FSInputFile(photo_path), caption=f"<b>{t(lang, title_key)}</b>")

    await message.answer(text, reply_markup=reply_markup)


def _asset_path(folder: str, filename: str | None, lang: str) -> Path | None:
    """Til bo'yicha media faylni topadi.

    Tartib: assets/<folder>/<lang>/<file> -> assets/<folder>/<default>/<file>
    -> assets/<folder>/<file> (eski tekis joylashuv).
    """
    if not filename:
        return None

    base = settings.assets_dir / folder
    candidates = [
        base / normalize(lang) / filename,
        base / DEFAULT_LANGUAGE / filename,
        base / filename,
    ]
    for path in candidates:
        if path.exists():
            return path
    return None
