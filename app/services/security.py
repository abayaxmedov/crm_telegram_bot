from __future__ import annotations

from app.db.models import Role


# Rol nomlari endi app/i18n.py da (role_label) lokalizatsiya qilinadi.

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
