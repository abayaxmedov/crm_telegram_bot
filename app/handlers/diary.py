from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, VisitDiary
from app.db.repositories import create_visit, list_visits, search_visits
from app.handlers.filters import RoleFilter
from app.handlers.utils import clean_optional, require_callback_user, require_user
from app.i18n import t, variants
from app.keyboards.reply import diary_inline, geo_request_keyboard, main_menu

router = Router(name="diary")


class DiaryFlow(StatesGroup):
    geo = State()
    note = State()
    query = State()


def _visit_line(visit: VisitDiary) -> str:
    when = str(visit.created_at)[:16] if visit.created_at else "-"
    coords = f"{visit.latitude}, {visit.longitude}" if visit.latitude is not None else "-"
    return f"#{visit.id} | {when} | 📍 {coords} | {visit.note or '-'}"


@router.message(F.text.in_(variants("btn_diary")), RoleFilter(Role.MANAGER))
async def diary_panel(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await require_user(message, session) is None:
        return
    await state.clear()
    await message.answer(t(lang, "diary_title"), reply_markup=diary_inline(lang))


@router.callback_query(F.data == "diary:new")
async def diary_new(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await require_callback_user(callback, session) is None:
        return
    await state.set_state(DiaryFlow.geo)
    await callback.message.answer(t(lang, "diary_send_geo"), reply_markup=geo_request_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "diary:last")
async def diary_last(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    rep = await require_callback_user(callback, session)
    if rep is None:
        return
    visits = await list_visits(session, rep, 5)
    if not visits:
        await callback.message.answer(t(lang, "diary_empty"))
    else:
        await callback.message.answer(
            t(lang, "diary_last_header") + "\n" + "\n".join(_visit_line(v) for v in visits)
        )
    await callback.answer()


@router.callback_query(F.data == "diary:search")
async def diary_search_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    if await require_callback_user(callback, session) is None:
        return
    await state.set_state(DiaryFlow.query)
    await callback.message.answer(t(lang, "diary_search_q"))
    await callback.answer()


@router.message(DiaryFlow.geo, F.text.in_(variants("btn_cancel")))
async def diary_cancel(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    await state.clear()
    await message.answer(t(lang, "diary_cancelled"), reply_markup=ReplyKeyboardRemove())
    if rep is not None:
        await message.answer(t(lang, "rep_back_menu"), reply_markup=main_menu(rep.role, lang))


@router.message(DiaryFlow.geo, F.location)
async def diary_got_geo(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(lat=str(message.location.latitude), lng=str(message.location.longitude))
    await state.set_state(DiaryFlow.note)
    await message.answer(t(lang, "diary_ask_note"), reply_markup=ReplyKeyboardRemove())


@router.message(DiaryFlow.geo)
async def diary_geo_invalid(message: Message, lang: str) -> None:
    await message.answer(t(lang, "diary_need_geo"))


@router.message(DiaryFlow.note)
async def diary_note(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    data = await state.get_data()
    visit = await create_visit(
        session,
        rep=rep,
        latitude=Decimal(data["lat"]),
        longitude=Decimal(data["lng"]),
        note=clean_optional(message.text),
    )
    await session.commit()
    await state.clear()
    await message.answer(t(lang, "diary_saved", id=visit.id, lat=data["lat"], lng=data["lng"]))
    await message.answer(t(lang, "rep_back_menu"), reply_markup=main_menu(rep.role, lang))


@router.message(DiaryFlow.query)
async def diary_do_search(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    rep = await require_user(message, session)
    if rep is None:
        return
    visits = await search_visits(session, rep, message.text or "")
    await state.clear()
    if not visits:
        await message.answer(t(lang, "diary_empty"), reply_markup=main_menu(rep.role, lang))
    else:
        await message.answer(
            t(lang, "diary_last_header") + "\n" + "\n".join(_visit_line(v) for v in visits),
            reply_markup=main_menu(rep.role, lang),
        )
