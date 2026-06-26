from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.db.models import FinanceType, RequestStatus, Role
from app.services.security import ROLE_CREATE_ORDER, ROLE_LABELS, can_create_role


BTN_MENU = "🏠 Asosiy menyu"
BTN_ADMIN = "👑 Admin"
BTN_DOCTORS = "🧑‍⚕️ Vrachlar"
BTN_PHARMACIES = "💊 Aptekalar"
BTN_DAILY = "🗒 Kundalik"
BTN_REQUESTS = "📦 Zayavkalar"
BTN_FINANCE = "💰 Finans"
BTN_SALARY = "🧾 Moy zarplata"


def reply_keyboard(rows: list[list[str]], *, placeholder: str = "Bo'limni tanlang") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item) for item in row] for row in rows],
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )


def main_menu(role: Role) -> ReplyKeyboardMarkup:
    if role == Role.OWNER:
        rows = [
            [BTN_ADMIN, BTN_DOCTORS],
            [BTN_PHARMACIES, BTN_DAILY],
            [BTN_REQUESTS, BTN_FINANCE],
            [BTN_SALARY],
        ]
    elif role == Role.MANAGER:
        rows = [
            [BTN_ADMIN, BTN_DOCTORS],
            [BTN_PHARMACIES, BTN_DAILY],
            [BTN_REQUESTS, BTN_SALARY],
        ]
    elif role in {Role.OPERATOR, Role.ASSISTANT}:
        rows = [[BTN_REQUESTS, BTN_DAILY], [BTN_DOCTORS, BTN_PHARMACIES], [BTN_SALARY]]
    else:
        rows = [[BTN_DAILY, BTN_SALARY], [BTN_REQUESTS]]
    return reply_keyboard(rows, placeholder="CRM bo'limini tanlang")


def back_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard([[BTN_MENU]])


def phone_number_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Telefon raqamingizni yuboring",
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard([["➕ User yaratish", "👥 Userlar"], [BTN_MENU]])


def doctors_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard([["➕ Vrach qo‘shish", "📋 Vrachlar ro‘yxati"], [BTN_MENU]])


def pharmacies_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard([["➕ Apteka qo‘shish", "📋 Aptekalar ro‘yxati"], [BTN_MENU]])


def daily_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard([["✍️ Hisobot qoldirish", "📋 Hisobotlar"], [BTN_MENU]])


def requests_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard([["➕ Zayavka yaratish", "📋 Zayavkalar"], [BTN_MENU]])


def finance_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard([["➕ Finans operatsiya", "📊 Finans hisobot"], [BTN_MENU]])


def salary_menu(is_owner: bool = False) -> ReplyKeyboardMarkup:
    rows = [["📋 Mening zarplatam"]]
    if is_owner:
        rows.insert(0, ["➕ Zarplata kiritish"])
    rows.append([BTN_MENU])
    return reply_keyboard(rows)


def role_inline_keyboard(actor_role: Role) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for role in ROLE_CREATE_ORDER:
        if can_create_role(actor_role, role):
            rows.append([InlineKeyboardButton(text=ROLE_LABELS[role], callback_data=f"create_role:{role.value}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def report_target_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Vrach", callback_data="report_target:doctor")],
            [InlineKeyboardButton(text="Apteka", callback_data="report_target:pharmacy")],
            [InlineKeyboardButton(text="Umumiy", callback_data="report_target:general")],
        ]
    )


def request_status_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Jarayonda", callback_data=f"request_status:{request_id}:{RequestStatus.IN_PROGRESS.value}"),
                InlineKeyboardButton(text="Bajarildi", callback_data=f"request_status:{request_id}:{RequestStatus.DONE.value}"),
            ],
            [InlineKeyboardButton(text="Bekor qilish", callback_data=f"request_status:{request_id}:{RequestStatus.CANCELED.value}")],
        ]
    )


def finance_type_keyboard() -> InlineKeyboardMarkup:
    labels = {
        FinanceType.INCOME: "Kirim",
        FinanceType.EXPENSE: "Chiqim",
        FinanceType.DEBT: "Qarzdorlik",
        FinanceType.PAYMENT: "To'lov",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"finance_type:{operation_type.value}")]
            for operation_type, label in labels.items()
        ]
    )
