from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role
from app.db.repositories import add_daily_report, list_daily_reports
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.i18n import t, variants
from app.keyboards.reply import daily_menu, report_target_keyboard
from app.services.media import answer_media

router = Router(name="reports")

# Kunlik hisobot YOZADIGAN rollar. Owner yozmaydi — faqat boshqalarning
# hisobotlarini ko'radi (top/product ham faqat o'qiydi, operator/doktor yozmaydi).
REPORT_WRITER_ROLES = {Role.MANAGER, Role.REGIONAL_MANAGER}


class DailyReportFlow(StatesGroup):
    target_name = State()
    body = State()


@router.message(F.text.in_(variants("btn_daily")))
async def daily_panel(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    await answer_media(
        message,
        screen="daily",
        text=t(lang, "daily_text"),
        lang=lang,
        reply_markup=daily_menu(lang, can_write=user.role in REPORT_WRITER_ROLES),
    )


@router.message(F.text.in_(variants("btn_report_add")))
async def report_start(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if user.role not in REPORT_WRITER_ROLES:
        await message.answer(t(lang, "section_closed"))
        return
    await message.answer(t(lang, "report_target_q"), reply_markup=report_target_keyboard(lang))


@router.callback_query(F.data.startswith("report_target:"))
async def report_target(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if user.role not in REPORT_WRITER_ROLES:
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return

    target_type = callback.data.split(":", 1)[1] if callback.data else "general"
    await state.update_data(target_type=target_type)
    await state.set_state(DailyReportFlow.target_name)
    await callback.message.answer(t(lang, "report_target_name_q"))
    await callback.answer()


@router.message(DailyReportFlow.target_name)
async def report_target_name(message: Message, state: FSMContext, lang: str) -> None:
    await state.update_data(target_name=clean_optional(message.text))
    await state.set_state(DailyReportFlow.body)
    await message.answer(t(lang, "report_body_q"))


@router.message(DailyReportFlow.body, F.voice)
async def report_voice(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
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
        text=t(lang, "report_voice_saved", id=report.id),
        lang=lang,
        reply_markup=daily_menu(lang),
    )


@router.message(DailyReportFlow.body)
async def report_text(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return

    body = clean_optional(message.text)
    if body is None:
        await message.answer(t(lang, "report_body_empty"))
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
        text=t(lang, "report_saved", id=report.id),
        lang=lang,
        reply_markup=daily_menu(lang),
    )


@router.message(F.text.in_(variants("btn_reports_list")))
async def reports_list(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return

    reports = await list_daily_reports(session, actor=user)
    if not reports:
        await message.answer(t(lang, "reports_empty"), reply_markup=daily_menu(lang, can_write=user.role in REPORT_WRITER_ROLES))
        return

    lines = []
    for report in reports:
        kind = "voice" if report.voice_file_id else "text"
        preview = (report.text or "").replace("\n", " ")[:80] or "-"
        lines.append(
            f"#{report.id} | {safe(report.target_type)} | {safe(report.target_name)} | {kind} | {escape(preview)}"
        )
    await message.answer(t(lang, "reports_header") + "\n\n" + "\n".join(lines), reply_markup=daily_menu(lang, can_write=user.role in REPORT_WRITER_ROLES))
