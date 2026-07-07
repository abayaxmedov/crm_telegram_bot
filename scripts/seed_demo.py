from __future__ import annotations

"""To'liq demo ma'lumot: har model uchun ~10 ta yozuv, bog'langan (FK butun).

Ichida: xodimlar (медвакил/оператор/ёрдамчи), врачлар, аптекалар, препаратлар,
договорлар, **медвакил шу ойлик сотувлари** (Продажи → врач бонуси + KPI факт),
складга заявкалар (турли статус), дневник (геолокация), ва **финанс**:
под-отчёт бериш / врачга тўлов / қайтариш (RepPayment) + owner финанс операциялари.

Скрипт `.env` даги DATABASE_URL га ёзади (Postgres ёки sqlite). Локалда:
    python scripts/seed_demo.py

Идемпотент: sentinel орқали иккинчи марта қўшмайди.
"""

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.db.models import (
    Contract,
    ContractStatus,
    DailyReport,
    Doctor,
    Drug,
    FinanceOperation,
    FinanceType,
    Pharmacy,
    RepPayment,
    RepPaymentKind,
    Request,
    RequestStatus,
    Role,
    Salary,
    Sale,
    SaleItem,
    User,
    VisitDiary,
    WarehouseRequest,
    WarehouseRequestItem,
    WarehouseStatus,
)
from app.db.session import AsyncSessionLocal, init_db

random.seed(42)
SENTINEL = "demo_seed_v1"

FIRST = ["Азиз", "Бекзод", "Дилшод", "Шерзод", "Отабек", "Жасур", "Санжар", "Фаррух", "Улуғбек", "Икром", "Нодир", "Комил"]
LAST = ["Каримов", "Юсупов", "Рахимов", "Тошматов", "Абдуллаев", "Эргашев", "Холматов", "Сафаров", "Назаров", "Мирзаев"]
CITIES = ["Тошкент", "Самарқанд", "Бухоро", "Андижон", "Наманган", "Фарғона", "Нукус", "Қарши", "Гулистон", "Урганч"]
RAYONS = ["Марказий", "Шимолий", "Жанубий", "Юнусобод", "Чилонзор", "Мирзо Улуғбек", "Сергели", "Яшнобод", "Олмазор", "Учтепа"]
PH_NAMES = ["Дори-Дармон", "Оила Фарм", "Соғлом", "Шифо", "Салом Фарм", "Табиб", "Зам-Зам", "Нур Фарм", "Медлайф", "Витамин"]
DRUGS = ["Аспирин", "Парацетамол", "Ибупрофен", "Амоксициллин", "Омепразол", "Метформин", "Аторвастатин", "Лоратадин", "Цитрамон", "Но-шпа"]
NOTES = ["Врач билан учрашув", "Аптека ташрифи", "Янги буюртма", "Презентация", "Танишув", "Қарздорлик бўйича", "Навбатдаги ташриф", "Шартнома имзоланди", "Маркетинг", "Назорат ташрифи"]
FIN_TITLES = ["Сотувдан кирим", "Ижара тўлови", "Транспорт харажати", "Ходимлар маоши", "Реклама", "Қарздорлик", "Етказиб берувчига тўлов", "Хом ашё", "Солиқ", "Бонус фонди"]


def full_name() -> str:
    return f"{random.choice(FIRST)} {random.choice(LAST)}"


def phone() -> str:
    return f"+9989{random.randint(0, 9)}{random.randint(1000000, 9999999)}"


def inn() -> str:
    return str(random.randint(100000000, 999999999))


def this_month_dt(now: datetime) -> datetime:
    start = now.replace(day=1, hour=8, minute=0, second=0, microsecond=0)
    max_days = max((now - start).days, 0)
    day_offset = random.randint(0, max_days) if max_days else 0
    return start + timedelta(days=day_offset, hours=random.randint(0, 8), minutes=random.randint(0, 59))


async def _already(session) -> bool:
    result = await session.execute(select(User).where(User.username == SENTINEL))
    return result.scalar_one_or_none() is not None


async def main() -> None:
    await init_db()
    now = datetime.utcnow()

    async with AsyncSessionLocal() as s:
        if await _already(s):
            print("Demo allaqachon mavjud (sentinel topildi). Qayta qo'shilmadi.")
            return

        # 1) XODIMLAR (10): 6 медвакил, 2 оператор, 2 ёрдамчи
        reps, operators, assistants = [], [], []
        tg = 900_000_000
        for i in range(6):
            u = User(
                telegram_id=tg + i,
                username=SENTINEL if i == 0 else f"demo_rep_{i}",
                full_name=full_name(),
                role=Role.MANAGER,
                is_active=True,
                language=random.choice(["uz_cyrl", "ru"]),
                region_city=random.choice(CITIES),
                region_rayon=random.choice(RAYONS),
                balance=Decimal("0"),
                phone_number=phone(),
            )
            s.add(u)
            reps.append(u)
        for i in range(2):
            u = User(telegram_id=tg + 10 + i, username=f"demo_op_{i}", full_name=full_name(),
                     role=Role.OPERATOR, is_active=True, language="ru", phone_number=phone())
            s.add(u)
            operators.append(u)
        for i in range(2):
            u = User(telegram_id=tg + 20 + i, username=f"demo_as_{i}", full_name=full_name(),
                     role=Role.ASSISTANT, is_active=True, language="ru", phone_number=phone())
            s.add(u)
            assistants.append(u)
        await s.flush()

        # 2) ПРЕПАРАТЛАР (10)
        drugs = []
        for dn in DRUGS:
            d = Drug(
                name=dn,
                stock=random.randint(300, 900),
                doctor_bonus_per_pack=Decimal(random.choice([5, 8, 10, 12, 15])),
                kpi_plan_qty=random.choice([100, 150, 200, 250, 300]),
                kpi_period_months=random.choice([1, 1, 1, 3, 6]),
                kpi_bonus_full=Decimal(random.choice([300, 400, 500, 600, 800])),
            )
            s.add(d)
            drugs.append(d)

        # 3) ВРАЧЛАР (10)
        doctors = []
        for _ in range(10):
            doc = Doctor(full_name=full_name(), phone_number=phone(), location_text=random.choice(CITIES),
                         class_category=random.choice(["A", "B", "C"]), manager_id=random.choice(reps).id,
                         bonus_balance=Decimal("0"))
            s.add(doc)
            doctors.append(doc)

        # 4) АПТЕКАЛАР (10)
        phs = []
        for i in range(10):
            ph = Pharmacy(name=PH_NAMES[i], phone_number=phone(), location_text=random.choice(CITIES),
                          responsible_person=full_name(), manager_id=random.choice(reps).id,
                          inn=inn(), filial=str(random.randint(1, 5)))
            s.add(ph)
            phs.append(ph)
        await s.flush()

        # 5) ДОГОВОРЛАР (10)
        contracts = []
        for i in range(10):
            c = Contract(pharmacy_id=phs[i].id, number=str(100 + i),
                         signed_date=f"{random.randint(1, 28):02d}.{random.randint(1, 9):02d}.2026",
                         status=ContractStatus.ACTIVE)
            s.add(c)
            contracts.append(c)

        # 6) СОТУВЛАР (18) — медвакил ШУ ОЙ сотгани (KPI факт + врач бонуси)
        for _ in range(18):
            rep = random.choice(reps)
            rep_docs = [d for d in doctors if d.manager_id == rep.id] or doctors
            rep_phs = [p for p in phs if p.manager_id == rep.id] or phs
            doc = random.choice(rep_docs)
            ph = random.choice(rep_phs)
            when = this_month_dt(now)
            sale = Sale(rep_id=rep.id, pharmacy_id=ph.id, doctor_id=doc.id, total_bonus=Decimal("0"), created_at=when)
            s.add(sale)
            await s.flush()
            total = Decimal("0")
            for _ in range(random.randint(2, 4)):
                dr = random.choice(drugs)
                qty = random.randint(10, 45)
                bonus = dr.doctor_bonus_per_pack * qty
                total += bonus
                s.add(SaleItem(sale_id=sale.id, drug_id=dr.id, drug_name=dr.name, quantity=qty, bonus=bonus, created_at=when))
                dr.stock = max(0, dr.stock - qty)
            sale.total_bonus = total
            doc.bonus_balance = (doc.bonus_balance or Decimal("0")) + total

        # 7) СКЛАДГА ЗАЯВКАЛАР (10) — турли статус
        statuses = [WarehouseStatus.NEW] * 4 + [WarehouseStatus.APPROVED] * 4 + [WarehouseStatus.REJECTED] * 2
        random.shuffle(statuses)
        for i in range(10):
            rep = random.choice(reps)
            ph = random.choice(phs)
            ph_contracts = [c for c in contracts if c.pharmacy_id == ph.id]
            req = WarehouseRequest(rep_id=rep.id, pharmacy_id=ph.id,
                                   contract_id=ph_contracts[0].id if ph_contracts else None, status=statuses[i])
            s.add(req)
            await s.flush()
            for _ in range(random.randint(1, 3)):
                dr = random.choice(drugs)
                s.add(WarehouseRequestItem(request_id=req.id, drug_id=dr.id, drug_name=dr.name, quantity=random.randint(5, 50)))

        # 8) ДНЕВНИК (10) — геолокацияли ташрифлар
        for _ in range(10):
            rep = random.choice(reps)
            s.add(VisitDiary(
                rep_id=rep.id,
                latitude=Decimal(str(round(41.2 + random.random() * 0.3, 6))),
                longitude=Decimal(str(round(69.1 + random.random() * 0.3, 6))),
                note=random.choice(NOTES),
                created_at=this_month_dt(now),
            ))

        # 9) ФИНАНС — RepPayment: под-отчёт бериш / врачга тўлов / қайтариш
        rep_payments = 0
        for rep in reps:  # 6 ta ISSUE (под отчёт berildi)
            issued = Decimal(random.choice([3000, 5000, 8000, 10000]))
            rep.balance = (rep.balance or Decimal("0")) + issued
            s.add(RepPayment(rep_id=rep.id, kind=RepPaymentKind.ISSUE, amount=issued, created_at=this_month_dt(now)))
            rep_payments += 1
        for rep in reps:  # врачга тўловлар
            for doc in [d for d in doctors if d.manager_id == rep.id and (d.bonus_balance or 0) > 0]:
                amount = min(rep.balance, doc.bonus_balance).quantize(Decimal("1"))
                if amount > 0:
                    rep.balance -= amount
                    doc.bonus_balance -= amount
                    s.add(RepPayment(rep_id=rep.id, doctor_id=doc.id, kind=RepPaymentKind.PAYOUT, amount=amount, created_at=this_month_dt(now)))
                    rep_payments += 1
                if rep_payments >= 12:
                    break
            if rep_payments >= 12:
                break
        idx = 0
        while rep_payments < 10:  # kamida 10 ta — qaytarish bilan to'ldiramiz
            rep = reps[idx % len(reps)]
            if rep.balance >= 200:
                rep.balance -= Decimal("200")
                s.add(RepPayment(rep_id=rep.id, kind=RepPaymentKind.RETURN, amount=Decimal("200"), created_at=this_month_dt(now)))
                rep_payments += 1
            idx += 1
            if idx > 30:
                break

        # 10) OWNER ФИНАНС ОПЕРАЦИЯЛАРИ (10)
        author = reps[0]
        for i in range(10):
            s.add(FinanceOperation(
                operation_type=random.choice(list(FinanceType)),
                amount=Decimal(random.randint(500, 20000)),
                title=FIN_TITLES[i],
                description="демо ма'лумот",
                created_by_id=author.id,
            ))

        # 11) ЗАРПЛАТА (eski model) (10)
        for _ in range(10):
            u = random.choice(reps + operators + assistants)
            base = Decimal(random.randint(2000, 6000))
            bonus = Decimal(random.randint(0, 2000))
            penalty = Decimal(random.randint(0, 500))
            s.add(Salary(user_id=u.id, month=f"{random.choice(['Июнь', 'Июль'])} 2026",
                         base_salary=base, bonus=bonus, penalty=penalty, total_amount=base + bonus - penalty,
                         status=random.choice(["paid", "unpaid"])))

        # 12) КУНДАЛИК ҲИСОБОТЛАР (eski model) (10)
        for _ in range(10):
            u = random.choice(reps + assistants)
            s.add(DailyReport(author_id=u.id, target_type=random.choice(["doctor", "pharmacy", "general"]),
                              target_name=random.choice(PH_NAMES), text=random.choice(NOTES)))

        # 13) ЗАЯВКАЛАР (eski model) (10)
        for i in range(10):
            u = random.choice(reps + assistants)
            s.add(Request(title=f"Заявка {i + 1}", description="демо заявка", status=random.choice(list(RequestStatus)),
                          created_by_id=u.id))

        await s.commit()

        # Hisobot
        async def cnt(model) -> int:
            return (await s.execute(select(func.count()).select_from(model))).scalar_one()

        print("Demo seed muvaffaqiyatli qo'shildi:")
        rows = [
            ("Xodimlar (User)", User), ("Врачлар", Doctor), ("Аптекалар", Pharmacy), ("Препаратлар", Drug),
            ("Договорлар", Contract), ("Сотувлар (Sale)", Sale), ("Сотув элементлари", SaleItem),
            ("Складга заявкалар", WarehouseRequest), ("Заявка элементлари", WarehouseRequestItem),
            ("Дневник (визит)", VisitDiary), ("Финанс (RepPayment)", RepPayment),
            ("Owner финанс операц.", FinanceOperation), ("Зарплата", Salary),
            ("Кундалик ҳисобот", DailyReport), ("Заявкалар (eski)", Request),
        ]
        for label, model in rows:
            print(f"  {label}: {await cnt(model)}")


if __name__ == "__main__":
    asyncio.run(main())
