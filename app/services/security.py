from __future__ import annotations

from app.db.models import Role, User


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


def can_add_doctors(role: Role) -> bool:
    """Doktor YARATISH: owner, TOP, product, regional menejer, medvakil (tasdiqsiz, to'g'ridan)."""
    return role in {
        Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.REGIONAL_MANAGER, Role.MANAGER,
    }


def can_edit_doctors(role: Role) -> bool:
    """Doktor ma'lumotlarini tahrirlash: owner, TOP menejer, product menejer."""
    return role in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}


def can_view_pharmacies(role: Role) -> bool:
    """Dorixonalar bo'limi: hisobot ko'ruvchilar + operator (owner'nikiday)."""
    return role in REPORT_VIEWER_ROLES or role == Role.OPERATOR


def creates_entity_approved(role: Role) -> bool:
    """Owner yaratgan doktor/dorixona to'g'ridan-to'g'ri APPROVED bo'ladi."""
    return role == Role.OWNER


def can_manage_lpu(role: Role) -> bool:
    """ЛПУ (Davolash-profilaktika muassasasi) ko'rish/yaratish: regional menejer va medvakil (+owner)."""
    return role in {Role.OWNER, Role.REGIONAL_MANAGER, Role.MANAGER}


def can_manage_wholesalers(role: Role) -> bool:
    """Оптом (ulgurji yetkazib beruvchi) yaratish/ko'rish — faqat OWNER."""
    return role == Role.OWNER


def can_add_wholesale_income(role: Role) -> bool:
    """Оптомдан приход kiritish — medvakil (+owner test/nazorat uchun)."""
    return role in {Role.OWNER, Role.MANAGER}


def can_approve_wholesale_income(role: Role) -> bool:
    """Оптомдан приход tasdig'i — TOP menejer (+owner)."""
    return role in {Role.OWNER, Role.TOP_MANAGER}


def doctor_visible_to(actor: User, doctor) -> bool:
    """Doktor actor ko'lamида ekanини tekshiradi (APPROVED holati alohida tekshiriladi).

    owner/top/product => hammasi;
    regional menejer => O'Z REGIONIdagi barcha doktorlar (o'zi yaratmagan bo'lsa ham —
      u region rahbari, jamoasining butun bazasi bilan ishlaydi);
    medvakil => FAQAT o'zi yaratgan (manager_id == actor.id).

    Dorixona qoidasi bilan bir xil (`pharmacy_visible_to`)."""
    if actor.role in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}:
        return True
    if actor.role == Role.REGIONAL_MANAGER:
        return doctor.region_id == actor.region_id
    if actor.role == Role.MANAGER:
        return doctor.manager_id == actor.id
    return False


def pharmacy_visible_to(actor: User, pharmacy) -> bool:
    """Dorixona actor ko'lamида ekanини tekshiradi (APPROVED holati alohida tekshiriladi).

    owner/top/product/operator => hammasi;
    regional menejer => o'z regioni (o'ziga tegishli);
    medvakil => faqat o'zi yaratgan (manager_id == actor.id)."""
    if actor.role in {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.OPERATOR}:
        return True
    if actor.role == Role.REGIONAL_MANAGER:
        return pharmacy.region_id == actor.region_id
    if actor.role == Role.MANAGER:
        return pharmacy.manager_id == actor.id
    return False


def can_approve_pharmacies(role: Role) -> bool:
    """Yangi dorixonani tasdiqlash: operator (va owner)."""
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
    """Dori (tovar) ma'lumotlarini (nom/narx/ball) yaratish/tahrirlash: PRODUCT menejer va owner."""
    return role in {Role.OWNER, Role.PRODUCT_MANAGER}


def can_record_sales(role: Role) -> bool:
    """Sotuvni bazaga kiritish: medvakil va regional menejer (owner cheklovsiz)."""
    return role in {Role.OWNER, Role.MANAGER, Role.REGIONAL_MANAGER}


def can_upload_materials(role: Role) -> bool:
    """Dori materiallarini yuklash: faqat PRODUCT menejer (owner ham faqat ko'radi)."""
    return role == Role.PRODUCT_MANAGER


def can_view_materials(role: Role) -> bool:
    return role in REPORT_VIEWER_ROLES


def can_use_webapp(role: Role) -> bool:
    """Analitika web-paneli: owner, TOP menejer, product menejer."""
    return role in ALL_REPORT_ROLES


def can_use_ball(role: Role) -> bool:
    """Ball balans bo'limi (balans ko'rish/yuborish)."""
    return role in {Role.OWNER, Role.TOP_MANAGER, Role.REGIONAL_MANAGER, Role.MANAGER}


# Owner ball (mint) yubora oladigan rollar — HAMMAGA (ball ishtirokchи menejerlar).
OWNER_BALL_TARGET_ROLES: frozenset[Role] = frozenset(
    {Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.REGIONAL_MANAGER, Role.MANAGER}
)


def ball_transfer_target_role(role: Role) -> Role | None:
    """Ball zanjiri: kim kimga o'tkaza oladi (owner'дан tashqari). None => o'tkaza olmaydi.

    owner -> HAMMAGA (OWNER_BALL_TARGET_ROLES, mint); TOP -> regional;
    regional -> o'z regioni medvakillari; medvakil -> doktor (alohida ro'yxat bilan)."""
    return {
        Role.OWNER: Role.TOP_MANAGER,  # legacy: owner uchun keng ro'yxat OWNER_BALL_TARGET_ROLES orqali
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
