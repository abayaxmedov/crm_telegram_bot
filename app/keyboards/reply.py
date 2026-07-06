from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.db.models import FinanceType, RequestStatus, Role
from app.i18n import LANGUAGE_NAMES, LANGUAGES, role_label, t
from app.services.security import ROLE_CREATE_ORDER, can_create_role


def reply_keyboard(rows: list[list[str]], *, placeholder: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item) for item in row] for row in rows],
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )


def main_menu(role: Role, lang: str) -> ReplyKeyboardMarkup:
    admin = t(lang, "btn_admin")
    doctors = t(lang, "btn_doctors")
    pharmacies = t(lang, "btn_pharmacies")
    daily = t(lang, "btn_daily")
    requests = t(lang, "btn_requests")
    finance = t(lang, "btn_finance")
    salary = t(lang, "btn_salary")
    language = t(lang, "btn_language")

    if role == Role.OWNER:
        rows = [
            [admin, doctors],
            [pharmacies, daily],
            [requests, finance],
            [salary, language],
        ]
    elif role == Role.MANAGER:
        # Медвакил (медпредставитель) menyusi — test3640bot uslubida.
        rows = [
            [doctors, pharmacies],
            [t(lang, "btn_sales"), t(lang, "btn_warehouse")],
            [t(lang, "btn_diary"), finance],
            [salary],
            [language],
        ]
    elif role == Role.OPERATOR:
        # Оператор фақат складга заявкаларни тасдиқлайди + тил.
        rows = [[t(lang, "btn_wh_approve")], [language]]
    elif role == Role.ASSISTANT:
        rows = [[requests, daily], [doctors, pharmacies], [salary, language]]
    else:
        rows = [[daily, salary], [requests], [language]]
    return reply_keyboard(rows, placeholder=t(lang, "ph_crm_section"))


def back_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard([[t(lang, "btn_menu")]], placeholder=t(lang, "ph_select_section"))


def phone_number_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_phone_share"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=t(lang, "ph_send_phone"),
    )


def language_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGE_NAMES[code], callback_data=f"set_lang:{code}")]
            for code in LANGUAGES
        ]
    )


def admin_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_user_create"), t(lang, "btn_users")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def doctors_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_doctor_add"), t(lang, "btn_doctors_list")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def pharmacies_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_pharmacy_add"), t(lang, "btn_pharmacies_list")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def daily_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_report_add"), t(lang, "btn_reports_list")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def requests_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_request_add"), t(lang, "btn_requests_list")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def finance_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_finance_add"), t(lang, "btn_finance_report")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def salary_menu(lang: str, is_owner: bool = False) -> ReplyKeyboardMarkup:
    rows = [[t(lang, "btn_salary_my")]]
    if is_owner:
        rows.insert(0, [t(lang, "btn_salary_add")])
    rows.append([t(lang, "btn_menu")])
    return reply_keyboard(rows, placeholder=t(lang, "ph_select_section"))


def role_inline_keyboard(actor_role: Role, lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for role in ROLE_CREATE_ORDER:
        if can_create_role(actor_role, role):
            rows.append(
                [InlineKeyboardButton(text=role_label(lang, role), callback_data=f"create_role:{role.value}")]
            )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def report_target_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "it_report_doctor"), callback_data="report_target:doctor")],
            [InlineKeyboardButton(text=t(lang, "it_report_pharmacy"), callback_data="report_target:pharmacy")],
            [InlineKeyboardButton(text=t(lang, "it_report_general"), callback_data="report_target:general")],
        ]
    )


def request_status_keyboard(request_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "it_status_in_progress"),
                    callback_data=f"request_status:{request_id}:{RequestStatus.IN_PROGRESS.value}",
                ),
                InlineKeyboardButton(
                    text=t(lang, "it_status_done"),
                    callback_data=f"request_status:{request_id}:{RequestStatus.DONE.value}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "it_status_cancel"),
                    callback_data=f"request_status:{request_id}:{RequestStatus.CANCELED.value}",
                )
            ],
        ]
    )


def finance_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    keys = {
        FinanceType.INCOME: "it_fin_income",
        FinanceType.EXPENSE: "it_fin_expense",
        FinanceType.DEBT: "it_fin_debt",
        FinanceType.PAYMENT: "it_fin_payment",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, key), callback_data=f"finance_type:{operation_type.value}")]
            for operation_type, key in keys.items()
        ]
    )


# ==================== Медвакил (медпредставитель) ====================

def rep_finance_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_pay_doctor")], [t(lang, "btn_return_admin")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def geo_request_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_send_geo"), request_location=True)],
            [KeyboardButton(text=t(lang, "btn_cancel"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=t(lang, "btn_send_geo"),
    )


def diary_inline(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_diary_new"), callback_data="diary:new")],
            [InlineKeyboardButton(text=t(lang, "btn_diary_search"), callback_data="diary:search")],
            [InlineKeyboardButton(text=t(lang, "btn_diary_last"), callback_data="diary:last")],
        ]
    )


def sale_cart_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_cart_add_more"), callback_data="sale_cart:add")],
            [InlineKeyboardButton(text=t(lang, "btn_cart_finish"), callback_data="sale_cart:finish")],
        ]
    )


def wh_cart_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_cart_add_more"), callback_data="wh_cart:add")],
            [InlineKeyboardButton(text=t(lang, "btn_cart_finish"), callback_data="wh_cart:finish")],
        ]
    )


def entities_inline(items: list[tuple[int, str]], prefix: str) -> InlineKeyboardMarkup:
    """items: [(id, label), ...] -> har biri callback_data f'{prefix}:{id}'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"{prefix}:{item_id}")] for item_id, label in items]
    )


def contracts_inline(contracts: list[tuple[int, str]], lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=f"wh_contract:{cid}")] for cid, label in contracts]
    rows.append([InlineKeyboardButton(text=t(lang, "btn_request_contract"), callback_data="wh_contract:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
