from __future__ import annotations

"""Demo ma'lumot: har bo'limga ~30 tadan yozuv qo'shish va ANIQ o'chirish.

Ishlatish:
    python scripts/demo_data.py seed [N]    # har bo'limga N (default 30) demo yozuv
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

from sqlalchemy import text

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

DEMO_TAG = "[DEMO]"  # nomlarga qo'shiladigan belgi (ko'zga ko'rinishi uchun)
RNG = random.Random(20260720)

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

    tr = Tracker()
    async with AsyncSessionLocal() as s:
        # ---------- Regionlar ----------
        regions = [Region(name=f"{DEMO_TAG} Регион {i+1}") for i in range(count)]
        s.add_all(regions)
        await s.flush()
        tr.add_all("regions", regions)

        # ---------- Xodimlar (turli rollar) ----------
        staff_roles = [
            Role.TOP_MANAGER, Role.PRODUCT_MANAGER, Role.REGIONAL_MANAGER,
            Role.MANAGER, Role.OPERATOR, Role.PHARMACY,
        ]
        users = []
        for i in range(count):
            role = staff_roles[i % len(staff_roles)]
            reg = RNG.choice(regions) if role in {Role.REGIONAL_MANAGER, Role.MANAGER, Role.OPERATOR} else None
            users.append(User(
                full_name=f"{DEMO_TAG} {role.value.title()} {i+1}",
                role=role,
                region_id=reg.id if reg else None,
                phone_number=f"9{RNG.randint(700000000, 999999999)}",
                ball_balance=RNG.randint(0, 5000),
                is_active=True,
            ))
        s.add_all(users)
        await s.flush()
        tr.add_all("users", users)
        managers = [u for u in users if u.role == Role.MANAGER] or users

        # ---------- ЛПУ ----------
        lpus = []
        for i in range(count):
            reg = RNG.choice(regions)
            lpus.append(Lpu(
                name=f"{DEMO_TAG} Клиника {i+1}",
                address=f"Демо кўча {i+1}",
                region_id=reg.id,
                created_by_id=RNG.choice(managers).id,
                approval_status=RNG.choice([ApprovalStatus.APPROVED, ApprovalStatus.APPROVED, ApprovalStatus.PENDING]),
            ))
        s.add_all(lpus)
        await s.flush()
        tr.add_all("lpus", lpus)

        # ---------- Dorilar ----------
        drugs = []
        for i in range(count):
            p100 = Decimal(RNG.randint(20, 400) * 1000)
            drugs.append(Drug(
                name=f"{DEMO_TAG} Препарат {i+1}",
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
            name=f"{DEMO_TAG} Оптом {i+1}",
            inn=f"{RNG.randint(100000000, 999999999)}",
            phone_number=f"9{RNG.randint(700000000, 999999999)}",
            created_by_id=managers[0].id,
        ) for i in range(count)]
        s.add_all(wholesalers)
        await s.flush()
        tr.add_all("wholesalers", wholesalers)

        # ---------- Doktorlar (kategoriya A/B/C uchun sotuv turlicha) ----------
        doctors = []
        for i in range(count):
            reg = RNG.choice(regions)
            lpu = RNG.choice([l for l in lpus if l.region_id == reg.id] or lpus)
            doctors.append(Doctor(
                full_name=f"{DEMO_TAG} Доктор {i+1}",
                phone_number=f"9{RNG.randint(700000000, 999999999)}",
                location_text=f"Демо манзил {i+1}",
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
        for i in range(count):
            reg = RNG.choice(regions)
            pharmacies.append(Pharmacy(
                name=f"{DEMO_TAG} Дорихона {i+1}",
                inn=f"{RNG.randint(100000000, 999999999)}",
                phone_number=f"9{RNG.randint(700000000, 999999999)}",
                location_text=f"Демо кўча {i+1}",
                responsible_person=f"Масъул {i+1}",
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
        contracts = []
        for i in range(count):
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
        for ph in appr_ph[:count]:
            for drug in RNG.sample(drugs, k=min(3, len(drugs))):
                stocks.append(dict(pharmacy_id=ph.id, drug_id=drug.id, quantity=RNG.randint(10, 300)))
        # PharmacyStock modelini import qilmasdan raw emas — modeldan foydalanamiz.
        from app.db.models import PharmacyStock
        stock_objs = [PharmacyStock(**st) for st in stocks]
        s.add_all(stock_objs)
        await s.flush()
        tr.add_all("pharmacy_stock", stock_objs)

        # ---------- Sotuvlar (+ SaleItem + SALE_DEDUCT tranzaksiya) ----------
        sales = []
        sale_ball_tx = []
        for i in range(count):
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
        for i in range(count):
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

        # ---------- Складга заявкалар (+ items) ----------
        wh_reqs = []
        for i in range(count):
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
        for i in range(count):
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
        for i in range(count):
            ttype = RNG.choice(["doctor", "pharmacy"])
            doc = RNG.choice(doctors)
            ph = RNG.choice(pharmacies)
            reports.append(DailyReport(
                author_id=RNG.choice(managers).id,
                target_type=ttype,
                target_name=(doc.full_name if ttype == "doctor" else ph.name),
                doctor_id=doc.id if ttype == "doctor" else None,
                pharmacy_id=ph.id if ttype == "pharmacy" else None,
                text=f"{DEMO_TAG} Ташриф изоҳи {i+1}",
                created_at=_days_ago(RNG.randint(0, 60)),
            ))
        s.add_all(reports)
        await s.flush()
        tr.add_all("daily_reports", reports)

        # ---------- Oyliklar ----------
        salaries = []
        for i in range(count):
            u = RNG.choice(users)
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
        for i in range(count):
            fins.append(FinanceOperation(
                operation_type=RNG.choice(list(FinanceType)),
                amount=Decimal(RNG.randint(100, 9000) * 1000),
                title=f"{DEMO_TAG} Операция {i+1}",
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
    print(f"🧹 Demo ma'lumot o'chirildi (jami {total} yozuv). Real ma'lumotга tegilmadi.")


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
