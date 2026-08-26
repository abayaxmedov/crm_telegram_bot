from __future__ import annotations

"""Demo ma'lumot: realistik (aralash o'zbek+rus) yozuvlar qo'shish va ANIQ o'chirish.

Ishlatish:
    python scripts/demo_data.py seed [N]    # N (default 30) -> "Katta" realistik to'plam
                                             # ~14 viloyat, ~30 vakil, ~120 doktor, ~90 dorixona
    python scripts/demo_data.py clear        # FAQAT demo yozuvlarni o'chiradi
    python scripts/demo_data.py status       # nechta demo yozuv borligini ko'rsatadi

MUHIM — REAL ma'lumot xavfsizligi:
    Har qo'shilgan demo yozuvning (jadval, id) si `demo_records` jadvaliga yoziladi.
    `clear` FAQAT shu ro'yxatdagi id'larni o'chiradi — real owner/doktor/sotuvga
    umuman tegmaydi (item jadvallari FK CASCADE bilan o'z-o'zidan o'chadi).
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, text

from app.db.models import (
    ApprovalStatus,
    BallTransaction,
    BallTxKind,
    BallTxStatus,
    Contract,
    ContractStatus,
    DailyReport,
    Doctor,
    Drug,
    FinanceOperation,
    FinanceType,
    Lpu,
    Pharmacy,
    Region,
    Role,
    Sale,
    SaleItem,
    Salary,
    User,
    WarehouseRequest,
    WarehouseRequestItem,
    WarehouseStatus,
    WholesaleIncome,
    WholesaleIncomeItem,
    Wholesaler,
)
from app.db.session import AsyncSessionLocal, engine

DEMO_TAG = "[DEMO]"  # legacy — endi nomlarda ishlatilmaydi; clear MANIFEST orqali ishlaydi.
RNG = random.Random(20260720)

# ======================= Realistik ma'lumot pool'lari (Kirill) =======================
# Regionlar — haqiqiy O'zbekiston viloyatlari (14 ta).
VILOYATS = [
    "Тошкент шаҳри", "Тошкент вилояти", "Самарқанд", "Бухоро", "Андижон",
    "Фарғона", "Наманган", "Қашқадарё", "Сурхондарё", "Хоразм",
    "Навоий", "Жиззах", "Сирдарё", "Қорақалпоғистон",
]

# Ismlar — aralash o'zbek + rus (foydalanuvchi tanlovi).
UZ_MALE = ["Абдулла", "Ботир", "Дилшод", "Жасур", "Сардор", "Улуғбек", "Феруз",
           "Шерзод", "Бекзод", "Отабек", "Санжар", "Аваз", "Нодир", "Хуршид", "Азиз"]
UZ_FEMALE = ["Дилноза", "Малика", "Нигора", "Севара", "Гулнора", "Зулфия",
             "Мадина", "Ойша", "Шаҳноза", "Феруза", "Камола", "Нозима"]
UZ_SURNAME = ["Каримов", "Раҳимов", "Юсупов", "Тошматов", "Абдуллаев", "Эргашев",
              "Мирзаев", "Умаров", "Холматов", "Насимов", "Йўлдошев", "Қодиров",
              "Исмоилов", "Турсунов", "Саидов"]

RU_MALE = ["Александр", "Дмитрий", "Сергей", "Иван", "Андрей", "Максим",
           "Николай", "Владимир", "Артём", "Павел"]
RU_FEMALE = ["Елена", "Ольга", "Наталья", "Ирина", "Светлана", "Татьяна",
             "Анна", "Марина", "Юлия", "Екатерина"]
RU_SURNAME = ["Иванов", "Петров", "Смирнов", "Кузнецов", "Соколов", "Попов",
              "Волков", "Морозов", "Новиков", "Фёдоров"]

# Dorilar — haqiqiy farmatsevtika nomlari.
DRUG_NAMES = [
    "Парацетамол 500мг", "Ибупрофен 400мг", "Амоксициллин 500мг", "Азитромицин 250мг",
    "Цефтриаксон 1г", "Омепразол 20мг", "Метформин 850мг", "Аторвастатин 20мг",
    "Лозартан 50мг", "Амлодипин 5мг", "Диклофенак 50мг", "Кетопрофен 100мг",
    "Лоратадин 10мг", "Цетиризин 10мг", "Дротаверин 40мг", "Ранитидин 150мг",
    "Фуросемид 40мг", "Эналаприл 10мг", "Флуконазол 150мг", "Ципрофлоксацин 500мг",
    "Доксициклин 100мг", "Нимесулид 100мг", "Мелоксикам 15мг", "Преднизолон 5мг",
    "Дексаметазон 4мг", "Глибенкламид 5мг", "Каптоприл 25мг", "Бисопролол 5мг",
    "Валсартан 80мг", "Спиронолактон 25мг", "Гентамицин 80мг", "Нистатин",
    "Аскорбин кислотаси", "Лоперамид 2мг", "Регидрон", "Хлоргексидин 0.05%",
    "Кларитромицин 500мг", "Пантопразол 40мг", "Розувастатин 10мг", "Индапамид 2.5мг",
]

PHARM_BRANDS = ["Dori-Darmon", "Оксил Фарм", "Шифо Аптека", "Саломат Фарм", "Нур Аптека",
                "Азиз Фарм", "Зам-Зам Фарм", "Мед Аптека", "Ихлос Фарм", "Дармон Плюс"]
CLINIC_BRANDS = ["Шифо", "Саломатлик", "Медлайн", "Нур Мед", "Ситора Мед",
                 "Оптима Мед", "Аква Мед", "Санита"]
STREETS = ["Амир Темур", "Мустақиллик", "Алишер Навоий", "Бобур", "Фурқат",
           "Шота Руставели", "Бунёдкор", "Чилонзор", "Мирзо Улуғбек", "Яшнобод",
           "Ойбек", "Зулфияхоним", "Лабзак", "Кичик ҳалқа йўли"]
VISIT_NOTES = [
    "Врач билан учрашув, препаратлар тақдим этилди",
    "Янги буюртма олинди",
    "Дорихона қолдиғи текширилди",
    "Акция шартлари тушунтирилди",
    "Ҳамкорлик бўйича музокара ўтказилди",
    "Тўлов масаласи муҳокама қилинди",
    "Янги препарат тақдимоти бўлди",
    "Шартнома янгиланди",
    "Мижоз эҳтиёжлари аниқланди",
    "Навбатдаги етказиб бериш режалаштирилди",
]
FIN_TITLES = ["Ижара тўлови", "Иш ҳақи", "Реклама харажати", "Транспорт харажати",
              "Коммунал тўлов", "Препарат хариди", "Бонус тўлови", "Солиқ тўлови",
              "Офис харажати", "Етказиб бериш"]


def _person_name() -> str:
    """Aralash o'zbek/rus, jinsga mos familiya (masc -ов, fem -ова)."""
    if RNG.random() < 0.65:  # ko'proq o'zbek
        if RNG.random() < 0.5:
            return f"{RNG.choice(UZ_MALE)} {RNG.choice(UZ_SURNAME)}"
        return f"{RNG.choice(UZ_FEMALE)} {RNG.choice(UZ_SURNAME)}а"
    if RNG.random() < 0.5:
        return f"{RNG.choice(RU_MALE)} {RNG.choice(RU_SURNAME)}"
    return f"{RNG.choice(RU_FEMALE)} {RNG.choice(RU_SURNAME)}а"


def _phone() -> str:
    """Real O'zbekiston mobil formati: +998 XX XXXXXXX."""
    code = RNG.choice(["90", "91", "93", "94", "95", "97", "98", "99", "88", "33"])
    return f"+998{code}{RNG.randint(1000000, 9999999)}"


def _inn() -> str:
    return f"{RNG.randint(100000000, 999999999)}"  # 9 xonali (O'zbekiston yuridik shaxs)


def _address(region: str) -> str:
    return f"{region}, {RNG.choice(STREETS)} кўчаси, {RNG.randint(1, 180)}-уй"


def _clinic_name(region: str) -> str:
    return RNG.choice([
        f"«{RNG.choice(CLINIC_BRANDS)}» клиникаси",
        f"«{RNG.choice(CLINIC_BRANDS)}» тиббиёт маркази",
        f"{region} марказий поликлиникаси",
        f"{RNG.randint(1, 12)}-сон оилавий поликлиника",
    ])


def _pharmacy_name(region: str) -> str:
    return RNG.choice([
        f"«{RNG.choice(PHARM_BRANDS)}» дорихона",
        f"«{RNG.choice(PHARM_BRANDS)}» дорихона №{RNG.randint(1, 40)}",
    ])


# clear paytida o'chirish tartibi (bolalar/bog'liqlar oldin, ota-onalar keyin).
# Item jadvallari FK CASCADE bilan o'chadi — bu yerda ular yo'q.
DELETE_ORDER = [
    "finance_operations",
    "salaries",
    "daily_reports",
    "ball_transactions",
    "wholesale_incomes",
    "warehouse_requests",
    "sales",
    "contracts",
    "pharmacy_stock",
    "doctors",
    "pharmacies",
    "lpus",
    "drugs",
    "wholesalers",
    "users",
    "regions",
]


async def _ensure_manifest(conn) -> None:
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS demo_records "
            "(table_name VARCHAR(64) NOT NULL, record_id INTEGER NOT NULL)"
        )
    )


class Tracker:
    """Yaratilgan demo yozuvlarni (jadval, id) sifatida to'playdi."""

    def __init__(self):
        self.rows: list[tuple[str, int]] = []

    def add(self, table: str, obj) -> None:
        self.rows.append((table, obj.id))

    def add_all(self, table: str, objs) -> None:
        for o in objs:
            self.rows.append((table, o.id))


def _days_ago(n: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


async def seed(count: int) -> None:
    async with engine.begin() as conn:
        await _ensure_manifest(conn)

    # ---- Miqdorlar (default count=30 -> "Katta" realistik to'plam) ----
    n_reps = count                       # med vakil (MANAGER) ~30
    n_doctors = count * 4                # ~120
    n_pharmacies = count * 3             # ~90
    n_lpus = max(14, count * 4 // 3)     # ~40
    n_wholesalers = max(6, count // 3)   # ~10
    n_sales = count * 5                  # ~150
    n_extra_tx = count * 3               # ~90
    n_wh = count * 2                     # ~60
    n_wi = count * 3 // 2                # ~45
    n_reports = count * 6                # ~180
    n_fins = count                       # ~30

    tr = Tracker()
    async with AsyncSessionLocal() as s:
        # ---------- Regionlar: MAVJUD (real) regionlarni ishlatamiz ----------
        # DB'da region bo'lsa (real deployment) — demo o'sha real regionlarga bog'lanadi
        # va ular manifestga TUSHMAYDI (clear real regionга tegmaydi, dublikat yaratilmaydi).
        # Faqat bo'sh bazada default viloyatlar (VILOYATS) yaratiladi va manifestga yoziladi.
        existing = (await s.execute(select(Region))).scalars().all()
        if existing:
            regions = list(existing)
        else:
            regions = [Region(name=v) for v in VILOYATS]
            s.add_all(regions)
            await s.flush()
            tr.add_all("regions", regions)

        # ---------- Xodimlar (realistik org tuzilma) ----------
        def _mk_user(role, region_id=None):
            return User(
                full_name=_person_name(), role=role, region_id=region_id,
                phone_number=_phone(), ball_balance=RNG.randint(0, 5000), is_active=True,
            )

        users = []
        for _ in range(2):
            users.append(_mk_user(Role.TOP_MANAGER))
        for _ in range(2):
            users.append(_mk_user(Role.PRODUCT_MANAGER))
        for reg in regions:                          # har regionga 1 ta regional menejer
            users.append(_mk_user(Role.REGIONAL_MANAGER, reg.id))
        for i in range(n_reps):                      # med vakillar, regionlarga taqsimlanadi
            users.append(_mk_user(Role.MANAGER, regions[i % len(regions)].id))
        for _ in range(max(3, len(regions) // 3)):   # operatorlar
            users.append(_mk_user(Role.OPERATOR, RNG.choice(regions).id))
        s.add_all(users)
        await s.flush()
        tr.add_all("users", users)
        managers = [u for u in users if u.role == Role.MANAGER] or users

        # ---------- ЛПУ ----------
        lpus = []
        for i in range(n_lpus):
            reg = RNG.choice(regions)
            lpus.append(Lpu(
                name=_clinic_name(reg.name),
                address=_address(reg.name),
                region_id=reg.id,
                created_by_id=RNG.choice(managers).id,
                approval_status=RNG.choice([ApprovalStatus.APPROVED, ApprovalStatus.APPROVED, ApprovalStatus.PENDING]),
            ))
        s.add_all(lpus)
        await s.flush()
        tr.add_all("lpus", lpus)

        # ---------- Dorilar (haqiqiy nomlar) ----------
        drug_names = DRUG_NAMES[:]
        RNG.shuffle(drug_names)
        drugs = []
        for name in drug_names:
            p100 = Decimal(RNG.randint(20, 400) * 1000)
            drugs.append(Drug(
                name=name,
                price_100=p100,
                price_50=p100 * Decimal("1.1"),
                price=p100,
                ball=RNG.randint(1, 20),
                kpi_plan_qty=RNG.choice([0, 50, 100, 200]),
                kpi_period_months=RNG.choice([1, 3, 6]),
                kpi_bonus_full=Decimal(RNG.randint(0, 2000) * 1000),
                is_active=True,
            ))
        s.add_all(drugs)
        await s.flush()
        tr.add_all("drugs", drugs)

        # ---------- Optomlar ----------
        wholesalers = [Wholesaler(
            name=f"«{RNG.choice(PHARM_BRANDS)}» оптом склад",
            inn=_inn(),
            phone_number=_phone(),
            created_by_id=managers[0].id,
        ) for _ in range(n_wholesalers)]
        s.add_all(wholesalers)
        await s.flush()
        tr.add_all("wholesalers", wholesalers)

        # ---------- Doktorlar (kategoriya A/B/C uchun sotuv turlicha) ----------
        doctors = []
        for i in range(n_doctors):
            reg = RNG.choice(regions)
            lpu = RNG.choice([l for l in lpus if l.region_id == reg.id] or lpus)
            doctors.append(Doctor(
                full_name=_person_name(),
                phone_number=_phone(),
                location_text=_address(reg.name),
                manager_id=RNG.choice(managers).id,
                region_id=reg.id,
                lpu_id=lpu.id,
                ball_balance=RNG.randint(0, 3000),
                approval_status=RNG.choice([ApprovalStatus.APPROVED, ApprovalStatus.APPROVED, ApprovalStatus.PENDING]),
                created_at=_days_ago(RNG.randint(40, 120)),
            ))
        s.add_all(doctors)
        await s.flush()
        tr.add_all("doctors", doctors)

        # ---------- Dorixonalar ----------
        pharmacies = []
        for i in range(n_pharmacies):
            reg = RNG.choice(regions)
            pharmacies.append(Pharmacy(
                name=_pharmacy_name(reg.name),
                inn=_inn(),
                phone_number=_phone(),
                location_text=_address(reg.name),
                responsible_person=_person_name(),
                manager_id=RNG.choice(managers).id,
                region_id=reg.id,
                ball_balance=RNG.randint(0, 2000),
                approval_status=RNG.choice([ApprovalStatus.APPROVED, ApprovalStatus.APPROVED, ApprovalStatus.PENDING]),
            ))
        s.add_all(pharmacies)
        await s.flush()
        tr.add_all("pharmacies", pharmacies)
        appr_ph = [p for p in pharmacies if p.approval_status == ApprovalStatus.APPROVED] or pharmacies
        appr_doc = [d for d in doctors if d.approval_status == ApprovalStatus.APPROVED] or doctors

        # ---------- Shartnomalar ----------
        n_contracts = max(1, len(appr_ph) * 2 // 3)
        contracts = []
        for i in range(n_contracts):
            ph = RNG.choice(pharmacies)
            contracts.append(Contract(
                pharmacy_id=ph.id,
                number=f"D-{1000+i}",
                signed_date=_days_ago(RNG.randint(1, 200)).strftime("%d.%m.%Y"),
                status=ContractStatus.ACTIVE,
            ))
        s.add_all(contracts)
        await s.flush()
        tr.add_all("contracts", contracts)

        # ---------- Dorixona qoldig'i ----------
        stocks = []
        for ph in appr_ph:
            for drug in RNG.sample(drugs, k=min(3, len(drugs))):
                stocks.append(dict(pharmacy_id=ph.id, drug_id=drug.id, quantity=RNG.randint(10, 300)))
        from app.db.models import PharmacyStock
        stock_objs = [PharmacyStock(**st) for st in stocks]
        s.add_all(stock_objs)
        await s.flush()
        tr.add_all("pharmacy_stock", stock_objs)

        # ---------- Sotuvlar (+ SaleItem + SALE_DEDUCT tranzaksiya) ----------
        sales = []
        sale_ball_tx = []
        for i in range(n_sales):
            rep = RNG.choice(managers)
            ph = RNG.choice(appr_ph)
            doc = RNG.choice(appr_doc)
            when = _days_ago(RNG.randint(0, 60))
            items_data = []
            total_price = Decimal("0")
            total_ball = 0
            for drug in RNG.sample(drugs, k=RNG.randint(1, 3)):
                qty = RNG.randint(1, 40)
                price = drug.price_100 or Decimal("0")
                items_data.append((drug, qty, price))
                total_price += price * qty
                total_ball += int(drug.ball or 0) * qty
            sale = Sale(rep_id=rep.id, pharmacy_id=ph.id, doctor_id=doc.id,
                        total_price=total_price, total_ball=total_ball, created_at=when)
            s.add(sale)
            await s.flush()
            for drug, qty, price in items_data:
                s.add(SaleItem(sale_id=sale.id, drug_id=drug.id, drug_name=drug.name,
                               quantity=qty, price=price, ball=int(drug.ball or 0), created_at=when))
            # Sotuvda doktordan ball ayirilishi (kategoriya analitikasi uchun)
            if total_ball > 0:
                tx = BallTransaction(kind=BallTxKind.SALE_DEDUCT, status=BallTxStatus.ACCEPTED,
                                     amount=total_ball, to_doctor_id=doc.id, sale_id=sale.id, created_at=when)
                s.add(tx)
                sale_ball_tx.append(tx)
            sales.append(sale)
        await s.flush()
        tr.add_all("sales", sales)
        tr.add_all("ball_transactions", sale_ball_tx)

        # ---------- Qo'shimcha ball tranzaksiyalari (MINT/TRANSFER/GIFT) ----------
        extra_tx = []
        for i in range(n_extra_tx):
            kind = RNG.choice([BallTxKind.TRANSFER, BallTxKind.GIFT, BallTxKind.MINT])
            status = RNG.choice([BallTxStatus.ACCEPTED, BallTxStatus.ACCEPTED, BallTxStatus.PENDING, BallTxStatus.REJECTED])
            extra_tx.append(BallTransaction(
                kind=kind, status=status, amount=RNG.randint(50, 3000),
                from_user_id=RNG.choice(users).id,
                to_doctor_id=RNG.choice(doctors).id if kind in {BallTxKind.TRANSFER, BallTxKind.GIFT} else None,
                to_user_id=RNG.choice(users).id if kind == BallTxKind.MINT else None,
                created_at=_days_ago(RNG.randint(0, 90)),
            ))
        s.add_all(extra_tx)
        await s.flush()
        tr.add_all("ball_transactions", extra_tx)

        # ---------- Doktor kategoriyasi spread (A/B/C teng ko'rinsin) ----------
        # Bot belgisi OXIRGI 30 KUN savdo tezligiga qarab: >=3000 A, 1500-3000 B, <1500 C.
        # Uchdan bir A, uchdan bir B, uchdan bir C bo'lishi uchun oxirgi 28 kunga
        # boshqariladigan SALE_DEDUCT tranzaksiyalar qo'shamiz.
        cat_tx = []
        for idx, doc in enumerate(doctors):
            bucket = idx % 3
            if bucket == 0:
                target = RNG.randint(3500, 6000)   # A: 30 kunda >=3000
            elif bucket == 1:
                target = RNG.randint(1600, 2900)   # B: 1500-3000
            else:
                target = RNG.randint(0, 1200)      # C: <1500
            remaining = target
            while remaining > 0:
                chunk = min(remaining, RNG.randint(300, 1500))
                cat_tx.append(BallTransaction(
                    kind=BallTxKind.SALE_DEDUCT, status=BallTxStatus.ACCEPTED, amount=chunk,
                    to_doctor_id=doc.id, created_at=_days_ago(RNG.randint(1, 28)),
                ))
                remaining -= chunk
        s.add_all(cat_tx)
        await s.flush()
        tr.add_all("ball_transactions", cat_tx)

        # ---------- Складга заявкалар (+ items) ----------
        wh_reqs = []
        for i in range(n_wh):
            ph = RNG.choice(appr_ph)
            req = WarehouseRequest(
                rep_id=RNG.choice(managers).id, pharmacy_id=ph.id,
                contract_id=RNG.choice(contracts).id,
                payment_percent=RNG.choice([50, 100]),
                status=RNG.choice([WarehouseStatus.NEW, WarehouseStatus.APPROVED, WarehouseStatus.REJECTED]),
                created_at=_days_ago(RNG.randint(0, 45)),
            )
            s.add(req)
            await s.flush()
            for drug in RNG.sample(drugs, k=RNG.randint(1, 3)):
                qty = RNG.randint(5, 100)
                s.add(WarehouseRequestItem(request_id=req.id, drug_id=drug.id, drug_name=drug.name,
                                           quantity=qty, shipped_quantity=qty if req.status == WarehouseStatus.APPROVED else 0,
                                           price=drug.price_100 or Decimal("0")))
            wh_reqs.append(req)
        await s.flush()
        tr.add_all("warehouse_requests", wh_reqs)

        # ---------- Оптомдан приходлар (+ items) ----------
        wi_incomes = []
        for i in range(n_wi):
            inc = WholesaleIncome(
                rep_id=RNG.choice(managers).id, pharmacy_id=RNG.choice(appr_ph).id,
                wholesaler_id=RNG.choice(wholesalers).id,
                status=RNG.choice([ApprovalStatus.PENDING, ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]),
                created_at=_days_ago(RNG.randint(0, 45)),
            )
            s.add(inc)
            await s.flush()
            for drug in RNG.sample(drugs, k=RNG.randint(1, 3)):
                s.add(WholesaleIncomeItem(income_id=inc.id, drug_id=drug.id, drug_name=drug.name,
                                          quantity=RNG.randint(5, 80)))
            wi_incomes.append(inc)
        await s.flush()
        tr.add_all("wholesale_incomes", wi_incomes)

        # ---------- Kundalik hisobotlar ----------
        reports = []
        for i in range(n_reports):
            ttype = RNG.choice(["doctor", "pharmacy"])
            doc = RNG.choice(doctors)
            ph = RNG.choice(pharmacies)
            reports.append(DailyReport(
                author_id=RNG.choice(managers).id,
                target_type=ttype,
                target_name=(doc.full_name if ttype == "doctor" else ph.name),
                doctor_id=doc.id if ttype == "doctor" else None,
                pharmacy_id=ph.id if ttype == "pharmacy" else None,
                text=RNG.choice(VISIT_NOTES),
                created_at=_days_ago(RNG.randint(0, 60)),
            ))
        s.add_all(reports)
        await s.flush()
        tr.add_all("daily_reports", reports)

        # ---------- Oyliklar (har xodimga bittadan) ----------
        salaries = []
        for u in users:
            base = Decimal(RNG.randint(2000, 8000) * 1000)
            bonus = Decimal(RNG.randint(0, 3000) * 1000)
            penalty = Decimal(RNG.randint(0, 500) * 1000)
            salaries.append(Salary(
                user_id=u.id, month=f"2026-{RNG.randint(1, 7):02d}",
                base_salary=base, bonus=bonus, penalty=penalty, total_amount=base + bonus - penalty,
            ))
        s.add_all(salaries)
        await s.flush()
        tr.add_all("salaries", salaries)

        # ---------- Moliya operatsiyalari ----------
        fins = []
        for i in range(n_fins):
            fins.append(FinanceOperation(
                operation_type=RNG.choice(list(FinanceType)),
                amount=Decimal(RNG.randint(100, 9000) * 1000),
                title=RNG.choice(FIN_TITLES),
                created_by_id=RNG.choice(users).id,
                created_at=_days_ago(RNG.randint(0, 90)),
            ))
        s.add_all(fins)
        await s.flush()
        tr.add_all("finance_operations", fins)

        # ---------- Manifest'ga yozamiz ----------
        for table, rid in tr.rows:
            await s.execute(
                text("INSERT INTO demo_records (table_name, record_id) VALUES (:t, :r)"),
                {"t": table, "r": rid},
            )
        await s.commit()

    # Xulosa
    from collections import Counter
    by_table = Counter(t for t, _ in tr.rows)
    print(f"✅ Demo ma'lumot qo'shildi (jami {len(tr.rows)} yozuv):")
    for table in DELETE_ORDER:
        if by_table.get(table):
            print(f"   {table:22} {by_table[table]}")


async def clear() -> None:
    async with engine.begin() as conn:
        await _ensure_manifest(conn)
    async with AsyncSessionLocal() as s:
        total = 0
        for table in DELETE_ORDER:
            ids = [r[0] for r in (await s.execute(
                text("SELECT record_id FROM demo_records WHERE table_name = :t"), {"t": table}
            )).all()]
            if not ids:
                continue
            # Faqat manifestdagi id'lar — item jadvallari FK CASCADE bilan o'chadi.
            # id'lar o'zimiz yozgan butun sonlar (manifest) — IN-literal xavfsiz va
            # ikkala bazada (Postgres/SQLite) bir xil ishlaydi.
            id_list = ",".join(str(int(i)) for i in ids)
            res = await s.execute(text(f"DELETE FROM {table} WHERE id IN ({id_list})"))
            total += res.rowcount or 0
            print(f"   {table:22} -{res.rowcount}")
        await s.execute(text("DELETE FROM demo_records"))
        await s.commit()
    print(f"🧹 Demo ma'lumot o'chirildi (jami {total} yozuv). Real ma'lumotга tegилmadi.")


async def status() -> None:
    async with engine.begin() as conn:
        await _ensure_manifest(conn)
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(
            text("SELECT table_name, count(*) FROM demo_records GROUP BY table_name ORDER BY table_name")
        )).all()
    if not rows:
        print("Demo ma'lumot yo'q (manifest bo'sh).")
        return
    print("Demo yozuvlar (manifest bo'yicha):")
    total = 0
    for table, cnt in rows:
        print(f"   {table:22} {cnt}")
        total += cnt
    print(f"   {'JAMI':22} {total}")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "seed":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        asyncio.run(seed(n))
    elif cmd == "clear":
        asyncio.run(clear())
    elif cmd == "status":
        asyncio.run(status())
    else:
        print(f"Noma'lum buyruq: {cmd}. Foydalanish: seed [N] | clear | status")
        sys.exit(1)


if __name__ == "__main__":
    main()
