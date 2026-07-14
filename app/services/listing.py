"""Sahifalangan + qidiriladigan ro'yxat komponenti.

Har qanday bo'limda ro'yxat 10 tadan ID bilan chiqadi, tagida ID tugmalari
(inline), ularning ostida ⬅️/➡️ (oldingi/keyingi 10) va 🔍 ном бўйича қидириш.

Ishlash tamoyili:
- Har bir ro'yxat turi ``ListSpec`` bilan ``REGISTRY`` da ro'yxatdan o'tadi.
- ``show_list`` ma'lumotni fetch qiladi, (ixtiyoriy) qidiruv bo'yicha filtrlaydi,
  sahifaga bo'ladi va matn + inline klaviaturани yuboradi/tahrirlaydi.
- Sahifa/qidiruv konteksti FSM ``_lists[key] = {"ctx":..., "query":...}`` da saqlanadi;
  navigatsiya tugmalari ``lst:{key}:{page|s|c}`` callback bilan (app/handlers/listing.py).
- Element ID tugmalari eski ``{pick_prefix}:{id}`` callback'ni saqlaydi — mavjud
  tanlash handlerlari o'zgarishsiz ishlaydi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Any, Awaitable, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Role, User
from app.db.repositories import (
    doctors_for_ball_transfer,
    list_active_drugs,
    list_all_drugs,
    list_doctors_visible,
    list_lpus_visible,
    list_materials,
    list_pharmacies_visible,
    list_pharmacy_stock,
    list_report_authors,
    list_users,
)
from app.i18n import role_label, t
from app.services.security import OWNER_BALL_TARGET_ROLES, ball_transfer_target_role

PAGE_SIZE = 10
PER_ROW = 5

FetchFn = Callable[[AsyncSession, User, dict], Awaitable[list[Any]]]
LabelFn = Callable[[Any], str]
RowFn = Callable[[Any, str], str]


@dataclass
class ListSpec:
    key: str  # registry kaliti (ikki nuqta ':' bo'lmasin)
    pick_prefix: str  # element tugmasi callback prefiksi ({pick_prefix}:{id})
    fetch: FetchFn
    label: LabelFn  # qidiruv + standart qator uchun (til-neytral nom)
    header_key: str
    empty_key: str
    row: RowFn | None = None  # ixtiyoriy maxsus qator (item, lang) -> str
    searchable: bool = True
    id_of: Callable[[Any], int] = field(default=lambda o: o.id)


_REGISTRY: dict[str, ListSpec] = {}


def register_list(spec: ListSpec) -> None:
    if ":" in spec.key:
        raise ValueError(f"ListSpec key ':' o'z ichiga olmasin: {spec.key}")
    _REGISTRY[spec.key] = spec


def get_spec(key: str) -> ListSpec | None:
    return _REGISTRY.get(key)


def _build_keyboard(
    spec: ListSpec, ids: list[int], page: int, pages: int, has_query: bool, lang: str
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for k in range(0, len(ids), PER_ROW):
        rows.append(
            [
                InlineKeyboardButton(text=str(i), callback_data=f"{spec.pick_prefix}:{i}")
                for i in ids[k : k + PER_ROW]
            ]
        )
    # Navigatsiya: ⬅️ (oldingi 10) va ➡️ (keyingi 10) — ID tugmalarining ikki yonида.
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_page_prev"), callback_data=f"lst:{spec.key}:{page - 1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_page_next"), callback_data=f"lst:{spec.key}:{page + 1}"))
    if nav:
        rows.append(nav)
    if spec.searchable:
        srow = [InlineKeyboardButton(text=t(lang, "btn_list_search"), callback_data=f"lst:{spec.key}:s")]
        if has_query:
            srow.append(InlineKeyboardButton(text=t(lang, "btn_list_clear"), callback_data=f"lst:{spec.key}:c"))
        rows.append(srow)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _row_text(spec: ListSpec, item: Any, lang: str) -> str:
    if spec.row is not None:
        return spec.row(item, lang)
    return f"#{spec.id_of(item)} | {escape(spec.label(item))}"


async def show_list(
    message: Message,
    session: AsyncSession,
    user: User,
    lang: str,
    state: FSMContext,
    key: str,
    *,
    ctx: dict | None = None,
    page: int = 0,
    query: str | None = None,
    edit: bool = False,
) -> None:
    """Ro'yxatni ko'rsatadi (yangi xabar yoki mavjudini tahrirlash)."""
    spec = get_spec(key)
    if spec is None:
        return
    ctx = ctx or {}
    query = (query or "").strip() or None

    items = await spec.fetch(session, user, ctx)
    if query:
        ql = query.casefold()
        items = [it for it in items if ql in spec.label(it).casefold()]

    total = len(items)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    chunk = items[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    # Kontekstni FSM'ga saqlaymiz (navigatsiya/qidiruv uchun) — holatni o'zgartirmaymiz.
    data = await state.get_data()
    lists = dict(data.get("_lists") or {})
    lists[key] = {"ctx": ctx, "query": query}
    await state.update_data(_lists=lists)

    if not chunk:
        if query:
            body = t(lang, "list_search_empty", q=escape(query))
        else:
            body = t(lang, spec.empty_key)
        text = body
    else:
        header = t(lang, spec.header_key)
        info = t(lang, "list_page_info", page=page + 1, pages=pages, total=total)
        if query:
            info += "  " + t(lang, "list_search_active", q=escape(query))
        rows = "\n".join(_row_text(spec, it, lang) for it in chunk)
        text = f"{header}\n{info}\n\n{rows}"

    kb = _build_keyboard(spec, [spec.id_of(it) for it in chunk], page, pages, bool(query), lang)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass  # tahrirlab bo'lmasa (bir xil kontent/eski xabar) — yangi yuboramiz
    await message.answer(text, reply_markup=kb)


# ==================== Standart ro'yxatlar ====================


async def _empty() -> list:
    return []


def _ph_label(p: Any) -> str:
    if getattr(p, "filial", None):
        return f"{p.name} (Филиал: {p.filial})"
    return p.name


def _drug_row(d: Any, lang: str) -> str:
    return f"#{d.id} | {escape(d.name)} ({t(lang, 'stock_short')}: {d.stock} | 💠 {int(d.ball or 0)})"


def _sale_drug_row(d: Any, lang: str) -> str:
    # Dorixona qoldig'i (остаток) — list_pharmacy_stock `_pharmacy_qty` biriktiradi.
    qty = getattr(d, "_pharmacy_qty", 0)
    return f"#{d.id} | {escape(d.name)} ({t(lang, 'stock_short')}: {qty} | 💠 {int(d.ball or 0)})"


def _drug_edit_row(d: Any, lang: str) -> str:
    return f"#{d.id} | {escape(d.name)} ({float(d.price or 0):,.2f} | 💠 {int(d.ball or 0)})"


def _doc_dir_row(d: Any, lang: str) -> str:
    phone = escape(str(d.phone_number)) if d.phone_number else "-"
    return f"#{d.id} | {escape(d.full_name)} | {phone} | 💠 {int(d.ball_balance or 0)}"


def _ph_dir_row(p: Any, lang: str) -> str:
    text = f"#{p.id} | {escape(p.name)}"
    if p.filial:
        text += f" (Ф: {escape(str(p.filial))})"
    inn = escape(str(p.inn)) if p.inn else "-"
    resp = escape(str(p.responsible_person)) if p.responsible_person else "-"
    return text + f" | ИНН {inn} | {resp}"


async def _fetch_ball_users(session: AsyncSession, user: User, ctx: dict) -> list[User]:
    query = (
        select(User)
        .options(selectinload(User.region))
        .where(User.is_active.is_(True), User.telegram_id.is_not(None))
        .order_by(User.full_name)
    )
    if user.role == Role.OWNER:
        # Owner HAMMAGA yuboradi (barcha ball ishtirokchи menejerlar).
        query = query.where(User.role.in_(OWNER_BALL_TARGET_ROLES))
    else:
        target_role = ball_transfer_target_role(user.role)
        if target_role is None:
            return []
        query = query.where(User.role == target_role)
        if user.role == Role.REGIONAL_MANAGER:
            query = query.where(User.region_id == user.region_id)
    return list((await session.execute(query)).scalars())


def _ball_user_label(u: Any) -> str:
    return u.full_name + (f" ({u.region.name})" if getattr(u, "region", None) else "")


def _ball_user_row(u: Any, lang: str) -> str:
    text = f"#{u.id} | {escape(u.full_name)} | {role_label(lang, u.role)}"
    if getattr(u, "region", None):
        text += f" | {escape(u.region.name)}"
    return text


def _users_row(u: Any, lang: str) -> str:
    tg = u.telegram_id if u.telegram_id is not None else "—"
    flag = "✅" if u.is_active else "🚫"
    return f"#{u.id} | {escape(u.full_name)} | {role_label(lang, u.role)} | {tg} {flag}"


def register_default_lists() -> None:
    # --- Doktorlar (ko'rish/tanlash) ---
    register_list(ListSpec(
        key="doc_dir", pick_prefix="doc_info",
        fetch=lambda s, u, c: list_doctors_visible(s, u, limit=5000),
        label=lambda d: d.full_name, row=_doc_dir_row,
        header_key="doctors_header", empty_key="doctors_empty",
    ))
    register_list(ListSpec(
        key="sale_doc", pick_prefix="sale_doc",
        fetch=lambda s, u, c: list_doctors_visible(s, u, limit=5000),
        label=lambda d: d.full_name,
        header_key="sales_choose_doctor", empty_key="sales_no_doctors",
    ))
    register_list(ListSpec(
        key="ball_doc", pick_prefix="ball_to_doc",
        fetch=lambda s, u, c: doctors_for_ball_transfer(s, u),
        label=lambda d: d.full_name,
        header_key="ball_choose_recipient", empty_key="ball_no_linked_doctors",
    ))
    register_list(ListSpec(
        key="rep_tgt_doctor", pick_prefix="rep_tgt:doctor",
        fetch=lambda s, u, c: list_doctors_visible(s, u, limit=5000),
        label=lambda d: d.full_name,
        header_key="report_pick_doctor", empty_key="report_no_doctors",
    ))

    # --- Dorixonalar (ko'rish/tanlash) ---
    register_list(ListSpec(
        key="ph_dir", pick_prefix="ph_info",
        fetch=lambda s, u, c: list_pharmacies_visible(s, u, limit=5000),
        label=lambda p: p.name, row=_ph_dir_row,
        header_key="pharmacies_header", empty_key="pharmacies_empty",
    ))
    register_list(ListSpec(
        key="sale_ph", pick_prefix="sale_ph",
        fetch=lambda s, u, c: list_pharmacies_visible(s, u, limit=5000),
        label=_ph_label,
        header_key="sales_choose_pharmacy", empty_key="sales_no_pharmacies",
    ))
    register_list(ListSpec(
        key="wh_ph", pick_prefix="wh_ph",
        fetch=lambda s, u, c: list_pharmacies_visible(s, u, limit=5000),
        label=_ph_label,
        row=lambda p, lang: f"#{p.id} | {escape(_ph_label(p))} | ИНН {escape(str(p.inn)) if p.inn else '-'}",
        header_key="wh_list_header", empty_key="wh_list_empty",
    ))
    register_list(ListSpec(
        key="rep_tgt_pharmacy", pick_prefix="rep_tgt:pharmacy",
        fetch=lambda s, u, c: list_pharmacies_visible(s, u, limit=5000),
        label=lambda p: p.name,
        header_key="report_pick_pharmacy", empty_key="report_no_pharmacies",
    ))

    # --- Dorilar ---
    register_list(ListSpec(
        key="sale_drug", pick_prefix="sale_drug",
        # Faqat tanlangan dorixonaда qoldig'i bor dorilar (остаток bilan).
        fetch=lambda s, u, c: list_pharmacy_stock(s, c["pharmacy_id"]) if c.get("pharmacy_id") else _empty(),
        label=lambda d: d.name, row=_sale_drug_row,
        header_key="sales_choose_drug", empty_key="sales_no_pharmacy_stock",
    ))
    register_list(ListSpec(
        key="wh_drug", pick_prefix="wh_drug",
        fetch=lambda s, u, c: list_active_drugs(s),
        label=lambda d: d.name,
        header_key="wh_choose_drug", empty_key="sales_no_drugs",
    ))
    register_list(ListSpec(
        key="drug_edit", pick_prefix="drug_edit",
        fetch=lambda s, u, c: list_all_drugs(s),
        label=lambda d: d.name, row=_drug_edit_row,
        header_key="drug_pick_edit", empty_key="drugs_empty",
    ))
    # Ombor kirim (owner) — dori tanlab ombor qoldig'iga qo'shadi. Row ombor (Drug.stock) ni ko'rsatadi.
    register_list(ListSpec(
        key="wh_intake", pick_prefix="whin",
        fetch=lambda s, u, c: list_all_drugs(s),
        label=lambda d: d.name, row=_drug_row,
        header_key="wh_intake_pick", empty_key="drugs_empty",
    ))

    # --- Materiallar ---
    register_list(ListSpec(
        key="material", pick_prefix="material",
        fetch=lambda s, u, c: list_materials(s, limit=5000),
        label=lambda m: m.title,
        header_key="materials_header", empty_key="materials_empty",
    ))

    # --- Ball qabul qiluvchilari (rol-asosli) ---
    register_list(ListSpec(
        key="ball_user", pick_prefix="ball_to_user",
        fetch=_fetch_ball_users, label=_ball_user_label, row=_ball_user_row,
        header_key="ball_choose_recipient", empty_key="ball_no_recipients",
    ))

    # --- Hisobot xodimlari (rol+region konteksti) ---
    register_list(ListSpec(
        key="rep_emp", pick_prefix="rep_emp",
        fetch=lambda s, u, c: list_report_authors(
            s, role=Role(c["role"]), region_id=c.get("region_id")
        ),
        label=lambda e: e.full_name,
        header_key="reports_emp_header", empty_key="reports_no_employees",
    ))

    # --- Foydalanuvchilar (owner) ---
    register_list(ListSpec(
        key="users", pick_prefix="user_info",
        fetch=lambda s, u, c: list_users(s, limit=5000),
        label=lambda x: x.full_name, row=_users_row,
        header_key="last_users", empty_key="no_users",
    ))

    # --- ЛПУ (regional/medvakil) ---
    register_list(ListSpec(
        key="lpu", pick_prefix="lpu_info",
        fetch=lambda s, u, c: list_lpus_visible(s, u, limit=5000),
        label=lambda x: x.name,
        header_key="lpus_header", empty_key="lpus_empty",
    ))


register_default_lists()
