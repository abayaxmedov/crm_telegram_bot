from __future__ import annotations

from app.db.models import Role


# Rol nomlari endi app/i18n.py da (role_label) lokalizatsiya qilinadi.

# Apteka (PHARMACY) roli yaratib bo'lmaydi — ro'yxatdan olib tashlandi.
ROLE_CREATE_ORDER: tuple[Role, ...] = (
    Role.OWNER,
    Role.MANAGER,
    Role.OPERATOR,
    Role.ASSISTANT,
    Role.DOCTOR,
)


def can_create_role(actor_role: Role, target_role: Role) -> bool:
    # Apteka roli hech kim tomonidan yaratilmaydi (owner ham).
    if target_role == Role.PHARMACY:
        return False
    if actor_role == Role.OWNER:
        return True
    if actor_role == Role.MANAGER:
        return target_role in {Role.OPERATOR, Role.ASSISTANT, Role.DOCTOR}
    return False


def can_manage_directories(role: Role) -> bool:
    """Vrachlar bo'limini boshqarish (owner, medvakil)."""
    return role in {Role.OWNER, Role.MANAGER}


def can_manage_pharmacies(role: Role) -> bool:
    """Apteka ma'lumotlarini saqlash: owner, medvakil va medvakil yordamchisi."""
    return role in {Role.OWNER, Role.MANAGER, Role.ASSISTANT}


def can_manage_requests(role: Role) -> bool:
    return role in {Role.OWNER, Role.MANAGER, Role.ASSISTANT}


def can_change_request_status(role: Role) -> bool:
    return role in {Role.OWNER}


def can_view_finance(role: Role) -> bool:
    return role == Role.OWNER


def can_approve_warehouse(role: Role) -> bool:
    """Складга заявкаларни тасдиқлаш: оператор (ва owner). Оператор фақат шуни қила олади."""
    return role in {Role.OWNER, Role.OPERATOR}
