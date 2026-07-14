from __future__ import annotations

from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalStatus, Role, User
from app.db.repositories import (
    add_daily_report,
    get_active_user,
    get_doctor,
    get_pharmacy,
    list_daily_reports,
    list_regions,
    period_window,
    reports_by_author,
)
from app.handlers.utils import clean_optional, require_callback_user, require_user, safe
from app.i18n import role_label, t, variants
from app.keyboards.reply import (
    daily_menu,
    entities_inline,
    report_geo_keyboard,
    report_period_keyboard,
    report_role_keyboard,
    report_target_keyboard,
)
from app.services.listing import show_list
from app.services.media import answer_media
from app.services.security import REGION_SCOPED_REPORT_ROLES, pharmacy_visible_to, reports_viewer_roles

router = Router(name="reports")

# Kunlik hisobot YOZADIGAN rollar (owner yozmaydi, faqat ko'radi).
REPORT_WRITER_ROLES = {Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.MANAGER, Role.REGIONAL_MANAGER}

# "Ҳисоботлар" bosilganda drill-down (rol->xodim->davr) ko'radigan rollar.
# MANAGER (medvakil) o'z hisobotlarini tekis ro'yxatda ko'radi.
REPORT_DRILL_ROLES = {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.REGIONAL_MANAGER}

_PERIOD_LABEL = {"5d": "period_5d", "10d": "period_10d", "30d": "period_30d", "all": "period_all"}


class DailyReportFlow(StatesGroup):
    body = State()
    geo = State()


def _target_in_scope(user: User, entity) -> bool:
    """Tanlangan doktor/dorixona APPROVED va yozuvchining ko'lamida (region) bo'lsin."""
    if entity is None or entity.approval_status != ApprovalStatus.APPROVED:
        return False
    if user.role in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return True
    return entity.region_id == user.region_id


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
    await message.answer(t(lang, "report_where_q"), reply_markup=report_target_keyboard(lang))


@router.callback_query(F.data.startswith("report_where:"))
async def report_where(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if user.role not in REPORT_WRITER_ROLES:
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    target_type = (callback.data or "report_where:doctor").split(":", 1)[1]
    key = "rep_tgt_doctor" if target_type == "doctor" else "rep_tgt_pharmacy"
    await show_list(callback.message, session, user, lang, state, key)
    await callback.answer()


@router.callback_query(F.data.startswith("rep_tgt:"))
async def report_target_pick(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_callback_user(callback, session)
    if user is None:
        return
    if user.role not in REPORT_WRITER_ROLES:
        await callback.answer(t(lang, "section_closed"), show_alert=True)
        return
    parts = (callback.data or "").split(":")  # rep_tgt:{type}:{id}
    if len(parts) != 3:
        await callback.answer()
        return
    target_type, target_id = parts[1], int(parts[2])
    if target_type == "doctor":
        entity = await get_doctor(session, target_id)
        name = entity.full_name if entity else None
        ok = _target_in_scope(user, entity)
    else:
        entity = await get_pharmacy(session, target_id)
        name = entity.name if entity else None
        # Dorixona: medvakil => faqat o'zi yaratgan; regional => o'z regioni.
        ok = (
            entity is not None
            and entity.approval_status == ApprovalStatus.APPROVED
            and pharmacy_visible_to(user, entity)
        )
    if not ok:
        await callback.answer(t(lang, "entity_not_found"), show_alert=True)
        return

    await state.update_data(target_type=target_type, target_id=target_id, target_name=name)
    await state.set_state(DailyReportFlow.body)
    await callback.message.answer(t(lang, "report_body_q"))
    await callback.answer()


@router.message(DailyReportFlow.body, F.voice)
async def report_voice(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None or message.voice is None:
        return
    await state.update_data(voice_file_id=message.voice.file_id, text=clean_optional(message.caption))
    await state.set_state(DailyReportFlow.geo)
    await message.answer(t(lang, "report_ask_geo"), reply_markup=report_geo_keyboard(lang))


@router.message(DailyReportFlow.body)
async def report_text(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return
    body = clean_optional(message.text)
    if body is None:
        await message.answer(t(lang, "report_body_empty"))
        return
    await state.update_data(text=body, voice_file_id=None)
    await state.set_state(DailyReportFlow.geo)
    await message.answer(t(lang, "report_ask_geo"), reply_markup=report_geo_keyboard(lang))


async def _finalize_report(message: Message, session, state, user, lang, *, lat, lng) -> None:
    data = await state.get_data()
    ttype = data["target_type"]
    report = await add_daily_report(
        session,
        author=user,
        target_type=ttype,
        target_name=data.get("target_name"),
        doctor_id=data.get("target_id") if ttype == "doctor" else None,
        pharmacy_id=data.get("target_id") if ttype == "pharmacy" else None,
        text=data.get("text"),
        voice_file_id=data.get("voice_file_id"),
        latitude=lat,
        longitude=lng,
    )
    await session.commit()
    await state.clear()
    await message.answer(
        t(lang, "report_done", id=report.id, target=safe(data.get("target_name"))),
        reply_markup=ReplyKeyboardRemove(),
    )
    await answer_media(
        message, screen="menu", text=t(lang, "menu_text"), lang=lang,
        reply_markup=daily_menu(lang, can_write=user.role in REPORT_WRITER_ROLES), sticker=False,
    )


@router.message(DailyReportFlow.geo, F.location)
async def report_geo(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        await state.clear()
        return
    loc = message.location
    await _finalize_report(
        message, session, state, user, lang,
        lat=Decimal(str(loc.latitude)), lng=Decimal(str(loc.longitude)),
    )


@router.message(DailyReportFlow.geo)
async def report_geo_skip(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        await state.clear()
        return
    await _finalize_report(message, session, state, user, lang, lat=None, lng=None)


def _target_label(report, lang: str) -> str:
    """Doktor/dorixona ikonkasi bilan nom (nom bo'lmasa — target_type)."""
    name = report.target_name or report.target_type or "-"
    if report.target_type == "doctor":
        return t(lang, "report_target_doctor", name=safe(name))
    if report.target_type == "pharmacy":
        return t(lang, "report_target_pharmacy", name=safe(name))
    return safe(name)


def _geo_suffix(report, lang: str) -> str:
    """Geolokatsiya bo'lsa — xaritaga havola (ixtiyoriy)."""
    if report.latitude is None or report.longitude is None:
        return ""
    url = f"https://maps.google.com/?q={report.latitude},{report.longitude}"
    return "\n" + t(lang, "report_geo_link", url=url)


def _report_line(report) -> str:
    kind = "voice" if report.voice_file_id else "text"
    preview = (report.text or "").replace("\n", " ")[:80] or "-"
    return f"#{report.id} | {safe(report.target_type)} | {safe(report.target_name)} | {kind} | {escape(preview)}"


def _can_view_author(actor: User, emp: User) -> bool:
    """actor emp'ning hisobotini ko'ra oladimi (rol ko'lami + regional region)."""
    if emp.role not in reports_viewer_roles(actor.role):
        return False
    if actor.role == Role.REGIONAL_MANAGER and emp.region_id != actor.region_id:
        return False
    return True


async def _show_employees(
    msg: Message, session: AsyncSession, user: User, lang: str, state: FSMContext, *, role: Role, region_id: int | None
) -> None:
    await show_list(
        msg, session, user, lang, state, "rep_emp", ctx={"role": role.value, "region_id": region_id}
    )


async def _guard_drill(callback: CallbackQuery, session: AsyncSession, lang: str) -> User | None:
    user = await require_callback_user(callback, session)
    if user is None:
        return None
    if user.role not in REPORT_DRILL_ROLES:
        await callback.answer(t(lang, "reports_no_perm_drill"), show_alert=True)
        return None
    return user


@router.message(F.text.in_(variants("btn_reports_list")))
async def reports_list(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await require_user(message, session)
    if user is None:
        return

    # Medvakil — o'z hisobotlarini tekis ro'yxatda ko'radi (hozirgidek).
    if user.role == Role.MANAGER:
        reports = await list_daily_reports(session, actor=user)
        menu = daily_menu(lang, can_write=True)
        if not reports:
            await message.answer(t(lang, "reports_empty"), reply_markup=menu)
            return
        text = t(lang, "reports_header") + "\n\n" + "\n".join(_report_line(r) for r in reports)
        await message.answer(text, reply_markup=menu)
        return

    if user.role not in REPORT_DRILL_ROLES:
        await message.answer(t(lang, "section_closed"))
        return

    # Regional — to'g'ridan o'z regioni medvakillari.
    if user.role == Role.REGIONAL_MANAGER:
        await _show_employees(message, session, user, lang, state, role=Role.MANAGER, region_id=user.region_id)
        return

    # Owner / TOP / product — avval rol tanlash.
    roles = reports_viewer_roles(user.role)
    await message.answer(t(lang, "reports_choose_role"), reply_markup=report_role_keyboard(roles, lang))


@router.callback_query(F.data.startswith("rep_role:"))
async def rep_pick_role(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await _guard_drill(callback, session, lang)
    if user is None:
        return
    role = Role(callback.data.split(":", 1)[1])
    if role not in reports_viewer_roles(user.role):
        await callback.answer(t(lang, "reports_no_perm_drill"), show_alert=True)
        return
    await callback.answer()
    if role in REGION_SCOPED_REPORT_ROLES:
        regions = await list_regions(session)
        if not regions:
            await callback.message.answer(t(lang, "reports_no_regions"))
            return
        await callback.message.answer(
            t(lang, "reports_choose_region"),
            reply_markup=entities_inline([(r.id, r.name) for r in regions], f"rep_reg:{role.value}"),
        )
        return
    # TOP / product — region yo'q, to'g'ridan xodimlar.
    await _show_employees(callback.message, session, user, lang, state, role=role, region_id=None)


@router.callback_query(F.data.startswith("rep_reg:"))
async def rep_pick_region(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str) -> None:
    user = await _guard_drill(callback, session, lang)
    if user is None:
        return
    parts = (callback.data or "").split(":")  # rep_reg:{role}:{region_id}
    if len(parts) != 3:
        await callback.answer()
        return
    role = Role(parts[1])
    region_id = int(parts[2])
    if role not in reports_viewer_roles(user.role):
        await callback.answer(t(lang, "reports_no_perm_drill"), show_alert=True)
        return
    # Regional o'z regionidan tashqarini so'ramasin.
    if user.role == Role.REGIONAL_MANAGER and region_id != user.region_id:
        await callback.answer(t(lang, "reports_no_perm_drill"), show_alert=True)
        return
    await callback.answer()
    await _show_employees(callback.message, session, lang, role=role, region_id=region_id)


@router.callback_query(F.data.startswith("rep_emp:"))
async def rep_pick_employee(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await _guard_drill(callback, session, lang)
    if user is None:
        return
    emp = await get_active_user(session, int(callback.data.split(":", 1)[1]))
    if emp is None or not _can_view_author(user, emp):
        await callback.answer(t(lang, "reports_no_perm_drill"), show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        t(lang, "reports_choose_period", name=safe(emp.full_name)),
        reply_markup=report_period_keyboard(lang, emp.id),
    )


@router.callback_query(F.data.startswith("rep_per:"))
async def rep_pick_period(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    user = await _guard_drill(callback, session, lang)
    if user is None:
        return
    parts = (callback.data or "").split(":")  # rep_per:{emp_id}:{period}
    if len(parts) != 3:
        await callback.answer()
        return
    emp = await get_active_user(session, int(parts[1]))
    period = parts[2]
    if emp is None or not _can_view_author(user, emp):
        await callback.answer(t(lang, "reports_no_perm_drill"), show_alert=True)
        return
    await callback.answer()

    start, end = period_window(period)
    reports = await reports_by_author(session, emp.id, start, end)
    period_name = t(lang, _PERIOD_LABEL.get(period, "period_all"))
    if not reports:
        await callback.message.answer(
            t(lang, "reports_author_empty", name=safe(emp.full_name), period=period_name)
        )
        return

    await callback.message.answer(
        t(lang, "reports_author_header", name=safe(emp.full_name), period=period_name, count=len(reports))
    )
    for r in reports:
        date = str(r.created_at)[:16]
        target = _target_label(r, lang)
        geo = _geo_suffix(r, lang)
        body = (r.text or "").replace("\n", " ")
        if r.voice_file_id:
            cap = t(lang, "report_voice_cap", date=date, target=target, text=(" | " + escape(body)) if body else "")
            cap = cap + geo
            try:
                await callback.message.answer_voice(voice=r.voice_file_id, caption=cap[:1024])
            except Exception:
                await callback.message.answer(cap)
        else:
            await callback.message.answer(
                t(lang, "report_row_text", date=date, target=target, text=escape(body) or "-") + geo
            )
