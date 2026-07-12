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
    regions = t(lang, "btn_regions")
    reports = t(lang, "btn_hierarchy_reports")
    material_upload = t(lang, "btn_material_upload")
    materials = t(lang, "btn_materials")
    ball = t(lang, "btn_ball")
    drugs = t(lang, "btn_drugs")
    webapp = t(lang, "btn_webapp")

    if role == Role.OWNER:
        # Owner — cheklovsiz: barcha bo'limlar ochiq.
        rows = [
            [admin, regions],
            [doctors, pharmacies],
            [drugs, ball],
            [daily, requests],
            [finance, salary],
            [reports, materials],
            [material_upload, webapp],
            [language],
        ]
    elif role == Role.TOP_MANAGER:
        # TOP menejer: faqat hisobotlar (barcha turdagi) + ball + web panel.
        rows = [
            [reports, finance],
            [doctors, pharmacies],
            [ball, webapp],
            [materials, language],
        ]
    elif role == Role.PRODUCT_MANAGER:
        # Product menejer: dori materiallarini yuklaydi + barcha hisobotlar.
        rows = [
            [material_upload, materials],
            [reports, finance],
            [doctors, pharmacies],
            [webapp, language],
        ]
    elif role == Role.REGIONAL_MANAGER:
        # Regional menejer: o'z regioni + sotuv/sklad + ball.
        rows = [
            [doctors, pharmacies],
            [t(lang, "btn_sales"), t(lang, "btn_warehouse")],
            [ball, reports],
            [materials, language],
        ]
    elif role == Role.MANAGER:
        # Медвакил: moliya o'rniga BALL bo'limi.
        rows = [
            [doctors, pharmacies],
            [t(lang, "btn_sales"), t(lang, "btn_warehouse")],
            [t(lang, "btn_diary"), ball],
            [salary, materials],
            [reports, language],
        ]
    elif role == Role.OPERATOR:
        # Оператор: склад + doktor/dorixona tasdig'i + dorixonalar bo'limi (owner'nikiday).
        rows = [
            [t(lang, "btn_wh_approve")],
            [t(lang, "btn_entity_approve")],
            [pharmacies, language],
        ]
    elif role == Role.DOCTOR:
        # Доктор: faqat til tanlash.
        rows = [[language]]
    else:
        # ASSISTANT (deprecated), PHARMACY, noma'lum — faqat til.
        rows = [[language]]
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


def regions_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_region_add"), t(lang, "btn_regions_list")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def materials_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [[t(lang, "btn_material_upload"), t(lang, "btn_materials")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def doctors_menu(lang: str, can_add: bool = True) -> ReplyKeyboardMarkup:
    rows = []
    if can_add:
        rows.append([t(lang, "btn_doctor_add"), t(lang, "btn_doctors_list")])
    else:
        rows.append([t(lang, "btn_doctors_list")])
    rows.append([t(lang, "btn_doctors_excel")])
    rows.append([t(lang, "btn_menu")])
    return reply_keyboard(rows, placeholder=t(lang, "ph_select_section"))


def pharmacies_menu(lang: str, can_add: bool = True) -> ReplyKeyboardMarkup:
    rows = []
    if can_add:
        rows.append([t(lang, "btn_pharmacy_add"), t(lang, "btn_pharmacies_list")])
    else:
        rows.append([t(lang, "btn_pharmacies_list")])
    rows.append([t(lang, "btn_pharmacies_excel")])
    rows.append([t(lang, "btn_menu")])
    return reply_keyboard(rows, placeholder=t(lang, "ph_select_section"))


def drugs_menu(lang: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            [t(lang, "btn_drug_add"), t(lang, "btn_drugs_list")],
            [t(lang, "btn_drug_edit")],
            [t(lang, "btn_menu")],
        ],
        placeholder=t(lang, "ph_select_section"),
    )


def ball_inline_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_ball_send"), callback_data="ball:send")],
            [InlineKeyboardButton(text=t(lang, "btn_ball_report"), callback_data="ball:report")],
        ]
    )


def ball_accept_keyboard(lang: str, tx_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_ball_accept"), callback_data=f"ball_acc:{tx_id}"),
                InlineKeyboardButton(text=t(lang, "btn_ball_reject"), callback_data=f"ball_rej:{tx_id}"),
            ]
        ]
    )


def excel_periods_keyboard(lang: str, prefix: str) -> InlineKeyboardMarkup:
    """Excel yuklab olish davrlari: callback '{prefix}:10d|30d|all'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_excel_10d"), callback_data=f"{prefix}:10d")],
            [InlineKeyboardButton(text=t(lang, "btn_excel_30d"), callback_data=f"{prefix}:30d")],
            [InlineKeyboardButton(text=t(lang, "btn_excel_all"), callback_data=f"{prefix}:all")],
        ]
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


def finance_menu(lang: str, is_owner: bool = True) -> ReplyKeyboardMarkup:
    if is_owner:
        rows = [[t(lang, "btn_finance_add"), t(lang, "btn_finance_report")]]
    else:
        # TOP/product menejer: faqat hisobot (operatsiya kiritish owner-only).
        rows = [[t(lang, "btn_finance_report")]]
    rows.append([t(lang, "btn_menu")])
    return reply_keyboard(rows, placeholder=t(lang, "ph_select_section"))


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


def location_request_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Apteka yaratishda: joylashuvni ulashish tugmasi (matn ham kiritish mumkin)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_send_geo"), request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=t(lang, "enter_location"),
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


def wh_method_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Sklad zayavka: aptekani topish usuli — INN orqali yoki ro'yxatdan."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_wh_by_inn"), callback_data="wh_method:inn")],
            [InlineKeyboardButton(text=t(lang, "btn_wh_by_list"), callback_data="wh_method:list")],
        ]
    )


def inline_id_grid(ids: list[int], prefix: str, per_row: int = 5) -> InlineKeyboardMarkup:
    """ID raqamli ixcham inline tugmalar to'ri (aptekalar ro'yxati tanlovi uchun)."""
    buttons = [InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:{i}") for i in ids]
    rows = [buttons[k : k + per_row] for k in range(0, len(buttons), per_row)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def entities_inline(items: list[tuple[int, str]], prefix: str) -> InlineKeyboardMarkup:
    """items: [(id, label), ...] -> har biri callback_data f'{prefix}:{id}'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"{prefix}:{item_id}")] for item_id, label in items]
    )


def contracts_inline(contracts: list[tuple[int, str]], lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=f"wh_contract:{cid}")] for cid, label in contracts]
    rows.append([InlineKeyboardButton(text=t(lang, "btn_request_contract"), callback_data="wh_contract:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
