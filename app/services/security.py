from __future__ import annotations

from app.db.models import Role


# Rol nomlari app/i18n.py da (role_label) lokalizatsiya qilinadi.

# Owner faqat quyidagi rollarni yaratadi (ASSISTANT/PHARMACY yaratilmaydi).
ROLE_CREATE_ORDER: tuple[Role, ...] = (
    Role.TOP_MANAGER,
    Role.PRODUCT_MANAGER,
    Role.REGIONAL_MANAGER,
    Role.MANAGER,
    Role.OPERATOR,
    Role.DOCTOR,
)

# Region so'raladigan rollar (owner user yaratganda).
ROLES_WITH_REGION: frozenset[Role] = frozenset({Role.REGIONAL_MANAGER, Role.MANAGER})

# Jamoa (ierarxik) hisobotini ko'radigan rollar.
REPORT_VIEWER_ROLES: frozenset[Role] = frozenset(
    {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.REGIONAL_MANAGER, Role.MANAGER}
)

# Barcha turdagi hisobotlarni (jumladan moliya hisobotini) ko'radiganlar.
ALL_REPORT_ROLES: frozenset[Role] = frozenset({Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER})


def can_create_role(actor_role: Role, target_role: Role) -> bool:
    """Foydalanuvchi (bot akkaunti) yaratish — FAQAT owner."""
    if target_role in {Role.PHARMACY, Role.ASSISTANT}:
        return False
    return actor_role == Role.OWNER


def can_manage_regions(role: Role) -> bool:
    return role == Role.OWNER


def can_view_directories(role: Role) -> bool:
    """Doktorlar bo'limini ko'rish (dorixonalar uchun can_view_pharmacies)."""
    return role in REPORT_VIEWER_ROLES


def can_add_directories(role: Role) -> bool:
    """Doktor/dorixona YARATISH: owner, regional menejer, medvakil.

    TOP/product menejerlar faqat ko'radi (ular uchun bu hisobot turi)."""
    return role in {Role.OWNER, Role.REGIONAL_MANAGER, Role.MANAGER}


def can_view_pharmacies(role: Role) -> bool:
    """Dorixonalar bo'limi: hisobot ko'ruvchilar + operator (owner'nikiday)."""
    return role in REPORT_VIEWER_ROLES or role == Role.OPERATOR


def creates_entity_approved(role: Role) -> bool:
    """Owner yaratgan doktor/dorixona to'g'ridan-to'g'ri APPROVED bo'ladi."""
    return role == Role.OWNER


def can_approve_entities(role: Role) -> bool:
    """Yangi doktor/dorixonani tasdiqlash: operator (va owner)."""
    return role in {Role.OWNER, Role.OPERATOR}


def can_view_hierarchy_reports(role: Role) -> bool:
    return role in REPORT_VIEWER_ROLES


def reports_viewer_roles(role: Role) -> list[Role]:
    """Owner kundalik-hisobot drill-down: actor qaysi roldagi xodimlar
    hisobotini ko'ra oladi.

    owner => TOP/product/regional/medvakil; TOP/product => regional/medvakil;
    regional => faqat medvakil (o'z regioni). Boshqalar => hech kim."""
    if role == Role.OWNER:
        return [Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.REGIONAL_MANAGER, Role.MANAGER]
    if role in {Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return [Role.REGIONAL_MANAGER, Role.MANAGER]
    if role == Role.REGIONAL_MANAGER:
        return [Role.MANAGER]
    return []


# Kundalik hisobot drill-down'da tanlangan rol region bo'yicha tanlanadimi.
REGION_SCOPED_REPORT_ROLES: frozenset[Role] = frozenset({Role.REGIONAL_MANAGER, Role.MANAGER})


def can_view_finance_report(role: Role) -> bool:
    """Moliya HISOBOTINI ko'rish: owner + TOP + product menejer."""
    return role in ALL_REPORT_ROLES


def can_add_finance_operation(role: Role) -> bool:
    """Moliya operatsiyasini KIRITISH: faqat owner."""
    return role == Role.OWNER


def can_manage_drugs(role: Role) -> bool:
    """Dori (tovar) narxi va ballini kiritish/tahrirlash: faqat owner."""
    return role == Role.OWNER


def can_record_sales(role: Role) -> bool:
    """Sotuvni bazaga kiritish: medvakil va regional menejer (owner cheklovsiz)."""
    return role in {Role.OWNER, Role.MANAGER, Role.REGIONAL_MANAGER}


def can_upload_materials(role: Role) -> bool:
    """Dori materiallarini yuklash: PRODUCT menejer (va owner). TOP dan olib tashlangan."""
    return role in {Role.OWNER, Role.PRODUCT_MANAGER}


def can_view_materials(role: Role) -> bool:
    return role in REPORT_VIEWER_ROLES


def can_use_webapp(role: Role) -> bool:
    """Analitika web-paneli: owner, TOP menejer, product menejer."""
    return role in ALL_REPORT_ROLES


def can_use_ball(role: Role) -> bool:
    """Ball balans bo'limi (balans ko'rish/yuborish)."""
    return role in {Role.OWNER, Role.TOP_MANAGER, Role.REGIONAL_MANAGER, Role.MANAGER}


def ball_transfer_target_role(role: Role) -> Role | None:
    """Ball zanjiri: kim kimga o'tkaza oladi. None => o'tkaza olmaydi.

    owner -> TOP (mint, cheksiz); TOP -> regional; regional -> o'z regioni medvakillari;
    medvakil -> doktor (alohida, doktor ro'yxati bilan ishlanadi)."""
    return {
        Role.OWNER: Role.TOP_MANAGER,
        Role.TOP_MANAGER: Role.REGIONAL_MANAGER,
        Role.REGIONAL_MANAGER: Role.MANAGER,
        Role.MANAGER: Role.DOCTOR,
    }.get(role)


def can_manage_requests(role: Role) -> bool:
    return role in REPORT_VIEWER_ROLES


def can_change_request_status(role: Role) -> bool:
    return role == Role.OWNER


def can_view_finance(role: Role) -> bool:
    """LEGACY nom: moliya bo'limi paneli (report view bilan bir xil)."""
    return can_view_finance_report(role)


def can_approve_warehouse(role: Role) -> bool:
    """Складга заявкаларни тасдиқлаш: оператор (ва owner)."""
    return role in {Role.OWNER, Role.OPERATOR}
