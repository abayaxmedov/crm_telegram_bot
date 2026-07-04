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
from app.i18n import status_label, t, variants
from app.keyboards.reply import request_status_keyboard, requests_menu
from app.services.media import answer_media
from app.services.security import can_change_request_status, can_manage_requests

router = Router(name="requests")


class RequestFlow(StatesGroup):
    title = State()
    description = State()


@router.message(F.text.in_(variants("btn_requests")))
async def requests_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_requests(user.role):
        await message.answer(t(lang, "requests_closed"))
        return
    await answer_media(message, screen="requests", text=t(lang, "requests_text"), lang=lang, reply_markup=requests_menu(lang))


@router.message(F.text.in_(variants("btn_request_add")))
async def request_start(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_manage_requests(user.role):
        await message.answer(t(lang, "no_perm_request_add"))
        return
    await state.set_state(RequestFlow.title)
    await message.answer(t(lang, "enter_request_title"))


@router.message(RequestFlow.title)
async def request_title(message: Message, state: FSMContext, lang: str) -> None:
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer(t(lang, "title_too_short"))
        return
    await state.update_data(title=title)
    await state.set_state(RequestFlow.description)
    await message.answer(t(lang, "enter_request_desc"))


@router.message(RequestFlow.description)
async def request_finish(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
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
        text=t(lang, "request_created", id=request.id, title=escape(request.title)),
        lang=lang,
        reply_markup=requests_menu(lang),
    )


@router.message(F.text.in_(variants("btn_requests_list")))
async def request_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    requests = await list_requests(session)
    if not requests:
        await message.answer(t(lang, "requests_empty"), reply_markup=requests_menu(lang))
        return

    for request in requests[:10]:
        text = (
            f"<b>#{request.id} {escape(request.title)}</b>\n"
            f"{t(lang, 'label_status')}: <code>{status_label(lang, request.status)}</code>\n"
            f"{t(lang, 'label_desc')}: {safe(request.description)}"
        )
        markup = request_status_keyboard(request.id, lang) if can_change_request_status(user.role) else None
        await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("request_status:"))
async def request_status(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_change_request_status(user.role):
        await callback.answer(t(lang, "no_perm_status"), show_alert=True)
        return

    _, request_id_raw, status_raw = callback.data.split(":", 2)
    request = await update_request_status(
        session,
        request_id=int(request_id_raw),
        status=RequestStatus(status_raw),
        actor=user,
    )
    if request is None:
        await callback.answer(t(lang, "request_not_found"), show_alert=True)
        return

    await session.commit()
    await callback.message.edit_text(
        f"<b>#{request.id} {escape(request.title)}</b>\n"
        f"{t(lang, 'label_status')}: <code>{status_label(lang, request.status)}</code>"
    )
    await callback.answer(t(lang, "status_updated"))
