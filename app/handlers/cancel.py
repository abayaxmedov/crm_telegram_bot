from __future__ import annotations

"""Global FSM bekor qilish.

Foydalanuvchi biror FSM holatida (masalan doktor qo'shish, ball miqdori kiritish,
shartnoma raqami) turganda REPLY-MENYU tugmasini bossa, tugma matni maydon qiymati
sifatida saqlanib qolmasligi yoki foydalanuvchi holat tuzog'ida qolib ketmasligi
uchun oqim bekor qilinadi va asosiy menyu ko'rsatiladi.

Bu router setup_routers'da BIRINCHI bo'lib ulanadi. Holat bo'lmasa (state=None)
SkipHandler orqali update keyingi routerlarga o'tadi — oddiy tugma ishlashi
o'zgarmaydi."""

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import get_user_by_telegram_id
from app.handlers.common import phone_number_required, request_phone_number
from app.i18n import all_button_texts, t, variants
from app.keyboards.reply import language_inline_keyboard, main_menu
from app.services.media import answer_media

router = Router(name="cancel")

ALL_BUTTONS = all_button_texts()
MENU_BUTTONS = variants("btn_menu")


@router.message(F.text.in_(ALL_BUTTONS))
async def cancel_flow_on_button(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await state.get_state() is None:
        # Holat yo'q — oddiy tugma bosilishi, keyingi routerlarga o'tkazamiz.
        raise SkipHandler

    if message.from_user is None:
        raise SkipHandler
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if user is None or not user.is_active:
        raise SkipHandler

    await state.clear()

    # Onboarding talablari saqlanadi: avval til, keyin telefon (holat qayta o'rnatiladi).
    if not user.language:
        await message.answer(t(lang, "choose_language"), reply_markup=language_inline_keyboard())
        return
    if phone_number_required(user):
        await request_phone_number(message, lang, state)
        return

    # Asosiy menyu tugmasi bo'lsa — shunchaki menyu; boshqa tugma bo'lsa
    # "amal bekor qilindi" eslatmasi bilan menyu (tugmani qayta bosish mumkin).
    if message.text not in MENU_BUTTONS:
        await message.answer(t(lang, "flow_cancelled"))
    await answer_media(
        message,
        screen="menu",
        text=t(lang, "menu_text"),
        lang=lang,
        reply_markup=main_menu(user.role, lang),
        sticker=False,
    )
