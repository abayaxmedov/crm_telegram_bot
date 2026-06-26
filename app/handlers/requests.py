from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RequestStatus
from app.db.repositories import add_request, list_requests, update_request_status
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.keyboards.reply import BTN_REQUESTS, request_status_keyboard, requests_menu
from app.services.media import answer_media
from app.services.security import can_change_request_status, can_manage_requests
from app.texts import REQUESTS_TEXT

router = Router(name="requests")


class RequestFlow(StatesGroup):
    title = State()
    description = State()


@router.message(F.text == BTN_REQUESTS)
async def requests_panel(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_requests(user.role):
        await message.answer("Zayavkalar bo'limi sizga ochilmagan.")
        return
    await answer_media(message, screen="requests", text=REQUESTS_TEXT, reply_markup=requests_menu())


@router.message(F.text == "➕ Zayavka yaratish")
async def request_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_requests(user.role):
        await message.answer("Zayavka yaratish uchun ruxsat yo'q.")
        return
    await state.set_state(RequestFlow.title)
    await message.answer("Zayavka sarlavhasini kiriting:")


@router.message(RequestFlow.title)
async def request_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer("Sarlavha juda qisqa.")
        return
    await state.update_data(title=title)
    await state.set_state(RequestFlow.description)
    await message.answer("Zayavka tavsifi. Agar kerak bo'lmasa `-` yuboring:")


@router.message(RequestFlow.description)
async def request_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    data = await state.get_data()
    request = await add_request(
        session,
        title=data["title"],
        description=clean_optional(message.text),
        created_by=user,
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=f"<b>Zayavka yaratildi:</b> #{request.id} {escape(request.title)}",
        reply_markup=requests_menu(),
    )


@router.message(F.text == "📋 Zayavkalar")
async def request_list(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    requests = await list_requests(session)
    if not requests:
        await message.answer("Zayavkalar hali yo'q.", reply_markup=requests_menu())
        return

    for request in requests[:10]:
        text = (
            f"<b>#{request.id} {escape(request.title)}</b>\n"
            f"Status: <code>{request.status.value}</code>\n"
            f"Tavsif: {safe(request.description)}"
        )
        markup = request_status_keyboard(request.id) if can_change_request_status(user.role) else None
        await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("request_status:"))
async def request_status(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_change_request_status(user.role):
        await callback.answer("Status o'zgartirish uchun ruxsat yo'q.", show_alert=True)
        return

    _, request_id_raw, status_raw = callback.data.split(":", 2)
    request = await update_request_status(
        session,
        request_id=int(request_id_raw),
        status=RequestStatus(status_raw),
        actor=user,
    )
    if request is None:
        await callback.answer("Zayavka topilmadi.", show_alert=True)
        return

    await session.commit()
    await callback.message.edit_text(
        f"<b>#{request.id} {escape(request.title)}</b>\nStatus: <code>{request.status.value}</code>"
    )
    await callback.answer("Status yangilandi.")

