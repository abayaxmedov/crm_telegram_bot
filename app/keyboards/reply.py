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
    wholesalers = t(lang, "btn_wholesalers")
    gift = t(lang, "btn_gift")

    if role == Role.OWNER:
        # Owner: dori katalogини (🧪) boshqaradi; material yuklash PRODUCT menejerда, owner faqat ko'radi.
        rows = [
            [admin, regions],
            [doctors, pharmacies],
            [drugs, ball],
            [wholesalers, t(lang, "btn_wi_approve")],
            [t(lang, "btn_gift_approve"), t(lang, "btn_entity_approve")],
            [t(lang, "btn_pharmacy_approve")],
            [t(lang, "btn_wh_approve")],
            [daily, requests],
            [finance, salary],
            [reports, materials],
            [webapp, language],
        ]
    elif role == Role.TOP_MANAGER:
        # TOP menejer: hisobotlar + kundalik + ball + web panel + doktor tasdig'i.
        rows = [
            [reports, daily],
            [doctors, pharmacies],
            [t(lang, "btn_wi_approve"), t(lang, "btn_gift_approve")],
            [t(lang, "btn_entity_approve")],
            [finance, ball],
            [materials, webapp],
            [language],
        ]
    elif role == Role.PRODUCT_MANAGER:
        # Product menejer: dori katalogи (🧪) + material yuklash + hisobotlar + kundalik.
        rows = [
            [drugs, material_upload],
            [materials, reports],
            [daily, doctors],
            [pharmacies, finance],
            [webapp, language],
        ]
    elif role == Role.REGIONAL_MANAGER:
        # Regional menejer: o'z regioni + sotuv/sklad + ball + ЛПУ.
        rows = [
            [doctors, pharmacies],
            [t(lang, "btn_lpu")],
            [t(lang, "btn_sales"), t(lang, "btn_warehouse")],
            [ball, gift],
            [reports, materials],
            [language],
        ]
    elif role == Role.MANAGER:
        # Медвакил: kundalik/tashrif birlashgan; ЛПУ bo'limi qo'shildi.
        rows = [
            [doctors, pharmacies],
            [t(lang, "btn_lpu")],
            [t(lang, "btn_sales"), t(lang, "btn_warehouse")],
            [t(lang, "btn_wholesale_income")],
            [ball, gift],
            [daily, salary],
            [materials, reports],
            [language],
        ]
    elif role == Role.OPERATOR:
        # Оператор: склад + dorixona tasdig'i + dorixonalar bo'limi (doktor tasdig'i TOP'ga o'tdi).
        rows = [
            [t(lang, "btn_wh_approve")],
            [t(lang, "btn_pharmacy_approve")],
            [pharmacies, language],
        ]
    elif role == Role.DOCTOR:
        # Доктор: salomlashuvsiz — faqat balans + til.
        rows = [[t(lang, "btn_doctor_balance")], [language]]
    elif role == Role.PHARMACY:
        # Дорихона mas'ul shaxsi: doktor kabi — balans + til.
        rows = [[t(lang, "btn_pharmacy_balance")], [language]]
    else:
        # ASSISTANT (deprecated), noma'lum — faqat til.
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


def user_manage_keyboard(lang: str, user_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Xodim kartasi ostidagi boshqaruv (faqat owner): tahrirlash/faolsizlantirish/o'chirish."""
    toggle_key = "btn_user_deactivate" if is_active else "btn_user_activate"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_user_edit"), callback_data=f"user_edit:{user_id}")],
            [InlineKeyboardButton(text=t(lang, toggle_key), callback_data=f"user_toggle:{user_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_user_delete"), callback_data=f"user_del:{user_id}")],
        ]
    )


def user_edit_menu_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    """Xodimda nimani tahrirlash: ism/telefon/rol/region."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_ue_name"), callback_data=f"ue_name:{user_id}"),
                InlineKeyboardButton(text=t(lang, "btn_ue_phone"), callback_data=f"ue_phone:{user_id}"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_ue_role"), callback_data=f"ue_role:{user_id}"),
                InlineKeyboardButton(text=t(lang, "btn_ue_region"), callback_data=f"ue_region:{user_id}"),
            ],
        ]
    )


def doctor_edit_menu_keyboard(lang: str, doctor_id: int) -> InlineKeyboardMarkup:
    """Doktorda nimani tahrirlash: ism/telefon/kategoriya/region/ЛПУ."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_de_name"), callback_data=f"de_name:{doctor_id}"),
                InlineKeyboardButton(text=t(lang, "btn_de_phone"), callback_data=f"de_phone:{doctor_id}"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_de_region"), callback_data=f"de_region:{doctor_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_de_lpu"), callback_data=f"de_lpu:{doctor_id}")],
        ]
    )


def user_edit_role_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    """Xodimga yangi rol tanlash (owner yarata oladigan rollar)."""
    rows = [
        [InlineKeyboardButton(text=role_label(lang, role), callback_data=f"uerole:{user_id}:{role.value}")]
        for role in ROLE_CREATE_ORDER
        if can_create_role(Role.OWNER, role)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_delete_confirm_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_user_delete_yes"), callback_data=f"user_del_yes:{user_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data=f"user_del_no:{user_id}")],
        ]
    )


def lpu_menu(lang: str, can_add: bool = True) -> ReplyKeyboardMarkup:
    rows = []
    if can_add:
        rows.append([t(lang, "btn_lpu_add"), t(lang, "btn_lpu_list")])
    else:
        rows.append([t(lang, "btn_lpu_list")])
    rows.append([t(lang, "btn_menu")])
    return reply_keyboard(rows, placeholder=t(lang, "ph_select_section"))


def gift_approve_keyboard(lang: str, tx_id: int) -> InlineKeyboardMarkup:
    """TOP menejer uchun: sovg'ani tasdiqlash / rad etish."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_entity_ok"), callback_data=f"gift_ok:{tx_id}"),
                InlineKeyboardButton(text=t(lang, "btn_entity_reject"), callback_data=f"gift_rej:{tx_id}"),
            ]
        ]
    )


def wholesalers_menu(lang: str) -> ReplyKeyboardMarkup:
    """Оптомлар bo'limi — faqat owner (yaratish + ro'yxat)."""
    return reply_keyboard(
        [[t(lang, "btn_wholesaler_add"), t(lang, "btn_wholesaler_list")], [t(lang, "btn_menu")]],
        placeholder=t(lang, "ph_select_section"),
    )


def wi_cart_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Оптомдан приход savati — yana qo'shish / yakunlash."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_cart_add_more"), callback_data="wi_cart:add")],
            [InlineKeyboardButton(text=t(lang, "btn_cart_finish"), callback_data="wi_cart:finish")],
        ]
    )


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


def ball_target_kind_keyboard(lang: str, *, with_user: bool, with_doctor: bool) -> InlineKeyboardMarkup:
    """Ball kimga: doktor / dorixona / xodim (rolga qarab)."""
    rows = []
    if with_doctor:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_ball_to_doctor"), callback_data="ball:to_doc")])
    if with_user:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_ball_to_user"), callback_data="ball:to_user")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_ball_to_pharmacy"), callback_data="ball:to_pha")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ball_accept_keyboard(lang: str, tx_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_ball_accept"), callback_data=f"ball_acc:{tx_id}"),
                InlineKeyboardButton(text=t(lang, "btn_ball_reject"), callback_data=f"ball_rej:{tx_id}"),
            ]
        ]
    )


def report_role_keyboard(roles, lang: str) -> InlineKeyboardMarkup:
    """Owner hisobot drill-down: rol tanlash (rep_role:{role})."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=role_label(lang, r), callback_data=f"rep_role:{r.value}")] for r in roles
        ]
    )


def report_period_keyboard(lang: str, emp_id: int) -> InlineKeyboardMarkup:
    """Xodim tanlangach davr (5/10/30 kun, hammasi) — rep_per:{emp_id}:{period}."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_period_5d"), callback_data=f"rep_per:{emp_id}:5d")],
            [InlineKeyboardButton(text=t(lang, "btn_period_10d"), callback_data=f"rep_per:{emp_id}:10d")],
            [InlineKeyboardButton(text=t(lang, "btn_period_30d"), callback_data=f"rep_per:{emp_id}:30d")],
            [InlineKeyboardButton(text=t(lang, "btn_period_all"), callback_data=f"rep_per:{emp_id}:all")],
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


def daily_menu(lang: str, can_write: bool = True) -> ReplyKeyboardMarkup:
    # can_write=False (owner): faqat boshqalarning hisobotlarini ko'radi, o'zi yozmaydi.
    if can_write:
        rows = [[t(lang, "btn_report_add"), t(lang, "btn_reports_list")]]
    else:
        rows = [[t(lang, "btn_reports_list")]]
    rows.append([t(lang, "btn_menu")])
    return reply_keyboard(rows, placeholder=t(lang, "ph_select_section"))


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
    """Hisobot/tashrif: qayerga borgani — doktorga yoki dorixonaga."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_where_doctor"), callback_data="report_where:doctor")],
            [InlineKeyboardButton(text=t(lang, "btn_where_pharmacy"), callback_data="report_where:pharmacy")],
        ]
    )


def report_geo_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Tashrif geolokatsiyasi (ixtiyoriy): yuborish yoki o'tkazib yuborish."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_send_geo"), request_location=True)],
            [KeyboardButton(text=t(lang, "skip_geo"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=t(lang, "btn_send_geo"),
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


def wh_payment_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Sklad zayavka: apteka boshlang'ich to'lov shartи — 100% yoki 50%.

    Tanlov dori narxini belgilaydi (price_100 / price_50)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_pay_100"), callback_data="wh_pay:100")],
            [InlineKeyboardButton(text=t(lang, "btn_pay_50"), callback_data="wh_pay:50")],
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
