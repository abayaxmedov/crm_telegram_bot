from __future__ import annotations

"""Медвакил zarplatasi — KPI hisoblagichi.

Har preparatда план (упак.), давр (1/3/6 ой) ва 100% бажарилганда тўлиқ бонус бор.
Факт = медвакил киритган сотувлар (Продажи) шу давр ичида.

FORMULA (созланадиган, тасдиқлаш керак):
  выполнение% = факт / план * 100
  яхлитланган% = floor(выполнение% / 10) * 10, макс 100   (мас. 1.5% -> 0%)
  KPI бонус = kpi_bonus_full * яхлитланган% / 100
"""

import calendar
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import list_active_drugs, sum_sales_qty


def _month_window(year: int, month: int, period_months: int) -> tuple[datetime, datetime, datetime]:
    """(start, end, end_of_current_month) — naive UTC (sqlite/pg mos)."""
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59)
    sy, sm = year, month - (period_months - 1)
    while sm <= 0:
        sm += 12
        sy -= 1
    start = datetime(sy, sm, 1, 0, 0, 0)
    return start, end, end


async def compute_kpi(session: AsyncSession, rep: User, now: datetime | None = None):
    now = now or datetime.utcnow()
    year, month = now.year, now.month

    results: list[dict] = []
    buckets: dict[int, Decimal] = {1: Decimal("0"), 3: Decimal("0"), 6: Decimal("0")}

    for drug in await list_active_drugs(session):
        if drug.kpi_plan_qty <= 0:
            continue
        period = drug.kpi_period_months if drug.kpi_period_months in (1, 3, 6) else 1
        start, end, _ = _month_window(year, month, period)

        fact = await sum_sales_qty(session, rep_id=rep.id, drug_id=drug.id, start=start, end=end)
        plan = drug.kpi_plan_qty
        pct = (Decimal(fact) / Decimal(plan) * 100) if plan else Decimal("0")
        rounded_pct = min(100, (int(pct) // 10) * 10)
        bonus = (Decimal(drug.kpi_bonus_full) * rounded_pct / 100).quantize(Decimal("0.01"))

        buckets[period] += bonus
        results.append(
            {
                "name": drug.name,
                "period": period,
                "start": start.strftime("%d.%m.%Y"),
                "end": end.strftime("%d.%m.%Y"),
                "plan": plan,
                "fact": fact,
                "pct": f"{pct:.1f}",
                "rpct": rounded_pct,
                "bonus": f"{bonus:.2f}",
            }
        )

    total = buckets[1] + buckets[3] + buckets[6]
    return results, buckets, total
