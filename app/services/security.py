from __future__ import annotations

from app.db.models import Role


ROLE_LABELS: dict[Role, str] = {
    Role.OWNER: "Owner",
    Role.MANAGER: "Menejer",
    Role.OPERATOR: "Operator",
    Role.ASSISTANT: "Operator yordamchisi",
    Role.DOCTOR: "Vrach",
    Role.PHARMACY: "Apteka",
}

ROLE_DESCRIPTIONS: dict[Role, str] = {
    Role.OWNER: "Barcha bo'limlarni boshqaradi, user yaratadi va hisobotlarni ko'radi.",
    Role.MANAGER: "Vrach/apteka ma'lumotlari, kundalik va zayavkalar bilan ishlaydi.",
    Role.OPERATOR: "Zayavkalar va operatsion jarayonlarni yuritadi.",
    Role.ASSISTANT: "Kuzatuv, kundalik va yordamchi vazifalarni bajaradi.",
    Role.DOCTOR: "O'ziga tegishli ma'lumot va zarplata bo'limlarini ko'radi.",
    Role.PHARMACY: "Apteka profiliga tegishli qismlardan foydalanadi.",
}

ROLE_CREATE_ORDER: tuple[Role, ...] = (
    Role.OWNER,
    Role.MANAGER,
    Role.OPERATOR,
    Role.ASSISTANT,
    Role.DOCTOR,
    Role.PHARMACY,
)


def can_create_role(actor_role: Role, target_role: Role) -> bool:
    if actor_role == Role.OWNER:
        return True
    if actor_role == Role.MANAGER:
        return target_role in {Role.OPERATOR, Role.ASSISTANT, Role.DOCTOR, Role.PHARMACY}
    return False


def can_manage_directories(role: Role) -> bool:
    return role in {Role.OWNER, Role.MANAGER}


def can_manage_requests(role: Role) -> bool:
    return role in {Role.OWNER, Role.MANAGER, Role.OPERATOR, Role.ASSISTANT}


def can_change_request_status(role: Role) -> bool:
    return role in {Role.OWNER, Role.OPERATOR}


def can_view_finance(role: Role) -> bool:
    return role == Role.OWNER

