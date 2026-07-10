from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import period_window, report_daily, report_sales, report_visits, reps_in_scope
from app.handlers.utils import require_callback_user, require_user
from app.i18n import t, variants
from app.services.excel import build_xlsx
from app.services.kpi import compute_kpi
from app.services.report_docx import build_report_docx
from app.services.security import can_view_hierarchy_reports

router = Router(name="reports_view")

IN_BOT_LIMIT = 8


def _fmt(value: object | None) -> str:
    return str(value) if value not in (None, "") else "-"


async def _gather_sections(session: AsyncSession, actor: User, lang: str) -> list[tuple[str, list[str]]]:
    """Bo'limlar: (sarlavha, [plain qatorlar]). DOCX va bot ichida ishlatiladi."""
    daily = await report_daily(session, actor)
    daily_lines = [
        f"#{r.id} | {_fmt(r.author.full_name if r.author else None)} | {_fmt(r.target_type)} | "
        f"{_fmt(r.target_name)} | {('[voice] ' if r.voice_file_id else '')}{(r.text or '').replace(chr(10), ' ')[:80]}"
        for r in daily
    ]

    sales = await report_sales(session, actor)
    sales_lines = [
        f"#{s.id} | {_fmt(s.rep.full_name if s.rep else None)} | "
        f"{_fmt(s.pharmacy.name if s.pharmacy else None)} | "
        f"{_fmt(s.doctor.full_name if s.doctor else None)} | "
        f"{len(s.items)} поз. | {s.total_price:,.2f} | 💠{s.total_ball} | {str(s.created_at)[:16]}"
        for s in sales
    ]

    visits = await report_visits(session, actor)
    visit_lines = [
        f"#{v.id} | {_fmt(v.rep.full_name if v.rep else None)} | "
        f"{_fmt(v.latitude)},{_fmt(v.longitude)} | {_fmt(v.note)} | {str(v.created_at)[:16]}"
        for v in visits
    ]

    kpi_lines = []
    for rep in await reps_in_scope(session, actor):
        _results, _buckets, total = await compute_kpi(session, rep)
        kpi_lines.append(f"{rep.full_name}: {total:,.2f}")

    return [
        (t(lang, "report_sec_daily"), daily_lines),
        (t(lang, "report_sec_sales"), sales_lines),
        (t(lang, "report_sec_visits"), visit_lines),
        (t(lang, "report_sec_kpi"), kpi_lines),
    ]


def _in_bot_text(lang: str, sections: list[tuple[str, list[str]]]) -> str:
    blocks: list[str] = []
    for header, lines in sections:
        shown = lines[:IN_BOT_LIMIT]
        body = "\n".join(escape(line) for line in shown) if shown else "—"
        if len(lines) > IN_BOT_LIMIT:
            body += "\n" + t(lang, "report_line_more", n=len(lines) - IN_BOT_LIMIT)
        blocks.append(f"<b>{escape(header)}</b>\n{body}")
    return "\n\n".join(blocks)


def _download_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_report_download_word"), callback_data="report_word")],
            [InlineKeyboardButton(text=t(lang, "btn_excel_10d"), callback_data="team_xlsx:10d")],
            [InlineKeyboardButton(text=t(lang, "btn_excel_30d"), callback_data="team_xlsx:30d")],
            [InlineKeyboardButton(text=t(lang, "btn_excel_all"), callback_data="team_xlsx:all")],
        ]
    )


@router.message(F.text.in_(variants("btn_hierarchy_reports")))
async def hierarchy_reports(message: Message, session: AsyncSession, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    if not can_view_hierarchy_reports(user.role):
        await message.answer(t(lang, "no_perm_reports"))
        return

    sections = await _gather_sections(session, user, lang)
    if all(not lines for _header, lines in sections):
        await message.answer(t(lang, "report_empty_all"))
        return

    await message.answer(_in_bot_text(lang, sections), reply_markup=_download_kb(lang))


@router.callback_query(F.data == "report_word")
async def hierarchy_reports_word(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_hierarchy_reports(user.role):
        await callback.answer(t(lang, "no_perm_reports"), show_alert=True)
        return

    await callback.answer()
    sections = await _gather_sections(session, user, lang)
    data = build_report_docx(t(lang, "report_docx_title"), sections)
    await callback.message.answer_document(
        document=BufferedInputFile(data, filename="team_report.docx"),
        caption=t(lang, "report_docx_caption"),
    )


@router.callback_query(F.data.startswith("team_xlsx:"))
async def hierarchy_reports_xlsx(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if not can_view_hierarchy_reports(user.role):
        await callback.answer(t(lang, "no_perm_reports"), show_alert=True)
        return

    await callback.answer()
    period = callback.data.split(":", 1)[1]
    start, end = period_window(period)

    daily = await report_daily(session, user, limit=5000, start=start, end=end)
    daily_rows = [
        [
            r.id,
            str(r.created_at)[:16],
            r.author.full_name if r.author else "-",
            r.target_type,
            r.target_name,
            "voice" if r.voice_file_id else "text",
            (r.text or "").replace("\n", " ")[:500],
        ]
        for r in daily
    ]

    sales = await report_sales(session, user, limit=5000, start=start, end=end)
    sales_rows = [
        [
            s.id,
            str(s.created_at)[:16],
            s.rep.full_name if s.rep else "-",
            s.pharmacy.name if s.pharmacy else "-",
            s.doctor.full_name if s.doctor else "-",
            sum(i.quantity for i in s.items),
            s.total_price,
            s.total_ball,
        ]
        for s in sales
    ]

    visits = await report_visits(session, user, limit=5000, start=start, end=end)
    visit_rows = [
        [
            v.id,
            str(v.created_at)[:16],
            v.rep.full_name if v.rep else "-",
            str(v.latitude) if v.latitude is not None else "-",
            str(v.longitude) if v.longitude is not None else "-",
            v.note,
        ]
        for v in visits
    ]

    kpi_rows = []
    for rep in await reps_in_scope(session, user):
        _results, _buckets, total = await compute_kpi(session, rep)
        kpi_rows.append([rep.full_name, total])

    data = build_xlsx(
        [
            (
                "Кундалик ҳисоботлар",
                ["ID", "Сана", "Ходим", "Тури", "Таргет", "Формат", "Матн"],
                daily_rows,
            ),
            (
                "Сотувлар",
                ["ID", "Сана", "Сотувчи", "Дорихона", "Доктор", "Упаковка", "Тушум", "Балл"],
                sales_rows,
            ),
            ("Ташрифлар", ["ID", "Сана", "Ходим", "Lat", "Lng", "Изоҳ"], visit_rows),
            ("KPI", ["Ходим", "Жами KPI (сўм)"], kpi_rows),
        ]
    )
    await callback.message.answer_document(
        document=BufferedInputFile(data, filename=f"team_report_{period}.xlsx"),
        caption=t(lang, "excel_caption_team", period=t(lang, f"period_{period}")),
    )
