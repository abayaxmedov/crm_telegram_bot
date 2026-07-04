from __future__ import annotations

"""Demo ma'lumot: препаратлар (ставка/план билан) ва аптекалар учун договорлар.

Медвакил оқимларини (Продажи, Заявка, Зарплата) синаб кўриш учун. Админ роли
тайёр бўлгач, буларни бот ичидан бошқариш имконияти қўшилади.

Ишга тушириш:
    python scripts/seed_demo.py
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db.models import Contract, ContractStatus, Drug, Pharmacy
from app.db.session import AsyncSessionLocal, init_db


# (nom, qoldiq, vrach_bonus/upak, kpi_plan, kpi_davr_oy, kpi_toliq_bonus)
DEMO_DRUGS = [
    ("TEST PREPORAT", 100, Decimal("10"), 200, 1, Decimal("500")),
    ("TEST PREPARAT NARXI", 100, Decimal("8"), 200, 1, Decimal("400")),
]


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        for name, stock, bonus, plan, period, kpi_full in DEMO_DRUGS:
            exists = (await session.execute(select(Drug).where(Drug.name == name))).scalar_one_or_none()
            if exists is None:
                session.add(
                    Drug(
                        name=name,
                        stock=stock,
                        doctor_bonus_per_pack=bonus,
                        kpi_plan_qty=plan,
                        kpi_period_months=period,
                        kpi_bonus_full=kpi_full,
                    )
                )

        pharmacies = (await session.execute(select(Pharmacy))).scalars().all()
        for pharmacy in pharmacies:
            has_contract = (
                await session.execute(select(Contract).where(Contract.pharmacy_id == pharmacy.id))
            ).first()
            if not has_contract:
                session.add(
                    Contract(
                        pharmacy_id=pharmacy.id,
                        number="1",
                        signed_date="20.05.2026",
                        status=ContractStatus.ACTIVE,
                    )
                )

        await session.commit()
    print("Demo seed done.")


if __name__ == "__main__":
    asyncio.run(main())
