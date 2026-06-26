from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import add_daily_report, list_daily_reports
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.keyboards.reply import BTN_DAILY, daily_menu, report_target_keyboard
from app.services.media import answer_media
from app.texts import DAILY_TEXT

router = Router(name="reports")


class DailyReportFlow(StatesGroup):
    target_name = State()
    body = State()


@router.message(F.text == BTN_DAILY)
async def daily_panel(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(message, screen="daily", text=DAILY_TEXT, reply_markup=daily_menu())


@router.message(F.text == "✍️ Hisobot qoldirish")
async def report_start(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await message.answer("Hisobot nimaga tegishli?", reply_markup=report_target_keyboard())


@router.callback_query(F.data.startswith("report_target:"))
async def report_target(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return

    target_type = callback.data.split(":", 1)[1] if callback.data else "general"
    await state.update_data(target_type=target_type)
    await state.set_state(DailyReportFlow.target_name)
    await callback.message.answer("Target nomi yoki izohini kiriting. Umumiy hisobot bo'lsa `-` yuboring:")
    await callback.answer()


@router.message(DailyReportFlow.target_name)
async def report_target_name(message: Message, state: FSMContext) -> None:
    await state.update_data(target_name=clean_optional(message.text))
    await state.set_state(DailyReportFlow.body)
    await message.answer("Hisobot matnini yozing yoki voice message yuboring:")


@router.message(DailyReportFlow.body, F.voice)
async def report_voice(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None or message.voice is None:
        return

    data = await state.get_data()
    report = await add_daily_report(
        session,
        author=user,
        target_type=data["target_type"],
        target_name=data.get("target_name"),
        text=clean_optional(message.caption),
        voice_file_id=message.voice.file_id,
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=f"<b>Voice hisobot saqlandi:</b> #{report.id}",
        reply_markup=daily_menu(),
    )


@router.message(DailyReportFlow.body)
async def report_text(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await require_user(message, session)
    if user is None:
        return

    body = clean_optional(message.text)
    if body is None:
        await message.answer("Hisobot matni bo'sh bo'lmasin.")
        return

    data = await state.get_data()
    report = await add_daily_report(
        session,
        author=user,
        target_type=data["target_type"],
        target_name=data.get("target_name"),
        text=body,
        voice_file_id=None,
    )
    await session.commit()
    await state.clear()
    await answer_media(
        message,
        screen="done",
        text=f"<b>Hisobot saqlandi:</b> #{report.id}",
        reply_markup=daily_menu(),
    )


@router.message(F.text == "📋 Hisobotlar")
async def reports_list(message: Message, session: AsyncSession) -> None:
    user = await require_user(message, session)
    if user is None:
        return

    reports = await list_daily_reports(session, actor=user)
    if not reports:
        await message.answer("Hali kundalik hisobotlar yo'q.", reply_markup=daily_menu())
        return

    lines = []
    for report in reports:
        kind = "voice" if report.voice_file_id else "text"
        preview = (report.text or "").replace("\n", " ")[:80] or "-"
        lines.append(
            f"#{report.id} | {safe(report.target_type)} | {safe(report.target_name)} | {kind} | {escape(preview)}"
        )
    await message.answer("<b>Kundalik hisobotlar</b>\n\n" + "\n".join(lines), reply_markup=daily_menu())

