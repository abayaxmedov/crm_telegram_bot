from __future__ import annotations

"""Analitika web-paneli (aiohttp) — owner / TOP menejer / product menejer uchun.

Barcha /api/* endpointlar `token` query-parametri bilan himoyalangan
(app/webapp/auth.py). Ma'lumotlar davr/region/rep filtrlariga ko'ra qaytadi."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from aiohttp import web
from sqlalchemy import select

from app.db.models import BallTxKind, BallTxStatus, Role, User
from app.db.repositories import (
    ball_balances_overview,
    ball_transactions_in_period,
    list_regions,
    list_sellers,
    sales_item_rows,
)
from app.db.session import AsyncSessionLocal
from app.webapp.auth import parse_token

STATIC_DIR = Path(__file__).resolve().parent / "static"

WEBAPP_ROLES = {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}


def _num(value) -> float | int:
    if isinstance(value, Decimal):
        return float(value)
    return value


async def _auth_user(request: web.Request, session) -> User | None:
    user_id = parse_token(request.query.get("token"))
    if user_id is None:
        return None
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active or user.role not in WEBAPP_ROLES:
        return None
    return user


def _parse_period(request: web.Request) -> tuple[datetime | None, datetime]:
    """period=10d|30d|all|custom (custom: start/end = YYYY-MM-DD). Aware UTC."""
    period = request.query.get("period", "30d")
    now = datetime.now(timezone.utc)
    if period == "custom":
        try:
            start = datetime.strptime(request.query["start"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = datetime.strptime(request.query["end"], "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        except (KeyError, ValueError):
            return now - timedelta(days=30), now
        return start, end
    if period == "10d":
        return now - timedelta(days=10), now
    if period == "all":
        return None, now
    return now - timedelta(days=30), now


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


async def index(request: web.Request) -> web.Response:
    return web.Response(
        text=(STATIC_DIR / "index.html").read_text(encoding="utf-8"),
        content_type="text/html",
    )


async def api_meta(request: web.Request) -> web.Response:
    async with AsyncSessionLocal() as session:
        user = await _auth_user(request, session)
        if user is None:
            return web.json_response({"error": "unauthorized"}, status=401)
        regions = await list_regions(session)
        sellers = await list_sellers(session)
        return web.json_response(
            {
                "user": {"name": user.full_name, "role": user.role.value},
                "regions": [{"id": r.id, "name": r.name} for r in regions],
                "reps": [
                    {
                        "id": u.id,
                        "name": u.full_name,
                        "role": u.role.value,
                        "region_id": u.region_id,
                        "region": u.region.name if u.region else None,
                    }
                    for u in sellers
                ],
            }
        )


async def api_summary(request: web.Request) -> web.Response:
    async with AsyncSessionLocal() as session:
        user = await _auth_user(request, session)
        if user is None:
            return web.json_response({"error": "unauthorized"}, status=401)

        start, end = _parse_period(request)
        region_id = _int_or_none(request.query.get("region_id"))
        rep_id = _int_or_none(request.query.get("rep_id"))

        rows = await sales_item_rows(session, start=start, end=end, region_id=region_id, rep_id=rep_id)

        totals = {
            "sales": len({r["sale_id"] for r in rows}),
            "qty": sum(r["qty"] for r in rows),
            "revenue": float(sum((r["revenue"] for r in rows), Decimal("0"))),
            "ball": sum(r["ball_total"] for r in rows),
        }

        by_region: dict[str, dict] = defaultdict(lambda: {"qty": 0, "revenue": Decimal("0"), "ball": 0, "sales": set()})
        by_rep: dict[str, dict] = defaultdict(lambda: {"qty": 0, "revenue": Decimal("0"), "ball": 0, "sales": set(), "region": None})
        by_day: dict[str, dict] = defaultdict(lambda: {"qty": 0, "revenue": Decimal("0")})
        by_drug: dict[str, dict] = defaultdict(lambda: {"qty": 0, "revenue": Decimal("0"), "ball": 0})

        for r in rows:
            region = r["region_name"] or "—"
            by_region[region]["qty"] += r["qty"]
            by_region[region]["revenue"] += r["revenue"]
            by_region[region]["ball"] += r["ball_total"]
            by_region[region]["sales"].add(r["sale_id"])

            # "Kim ishladi" kesimi — doktor EGASI bo'yicha (sotuvni kim kiritganidan
            # qat'i nazar). Doktorsiz sotuv bo'lsa — alohida guruh.
            rep = r["owner_name"] or "— (докторсиз)"
            by_rep[rep]["qty"] += r["qty"]
            by_rep[rep]["revenue"] += r["revenue"]
            by_rep[rep]["ball"] += r["ball_total"]
            by_rep[rep]["sales"].add(r["sale_id"])
            by_rep[rep]["region"] = r["region_name"]

            if r["created_at"] is not None:
                day = str(r["created_at"])[:10]
                by_day[day]["qty"] += r["qty"]
                by_day[day]["revenue"] += r["revenue"]

            drug = r["drug_name"]
            by_drug[drug]["qty"] += r["qty"]
            by_drug[drug]["revenue"] += r["revenue"]
            by_drug[drug]["ball"] += r["ball_total"]

        return web.json_response(
            {
                "totals": totals,
                "by_region": [
                    {"name": k, "sales": len(v["sales"]), "qty": v["qty"], "revenue": float(v["revenue"]), "ball": v["ball"]}
                    for k, v in sorted(by_region.items(), key=lambda kv: -kv[1]["qty"])
                ],
                "by_rep": [
                    {
                        "name": k,
                        "region": v["region"],
                        "sales": len(v["sales"]),
                        "qty": v["qty"],
                        "revenue": float(v["revenue"]),
                        "ball": v["ball"],
                    }
                    for k, v in sorted(by_rep.items(), key=lambda kv: -kv[1]["qty"])
                ],
                "by_day": [
                    {"day": k, "qty": v["qty"], "revenue": float(v["revenue"])} for k, v in sorted(by_day.items())
                ],
                "by_drug": [
                    {"name": k, "qty": v["qty"], "revenue": float(v["revenue"]), "ball": v["ball"]}
                    for k, v in sorted(by_drug.items(), key=lambda kv: -kv[1]["qty"])
                ],
            }
        )


async def api_ball(request: web.Request) -> web.Response:
    async with AsyncSessionLocal() as session:
        user = await _auth_user(request, session)
        if user is None:
            return web.json_response({"error": "unauthorized"}, status=401)

        start, end = _parse_period(request)
        region_id = _int_or_none(request.query.get("region_id"))
        rep_id = _int_or_none(request.query.get("rep_id"))

        users, doctors = await ball_balances_overview(session, user)
        txs = await ball_transactions_in_period(session, user, start, end)

        # Frontend filtrlari ball bo'limiga ham qo'llanadi (region/sotuvchi kesimi).
        if region_id is not None:
            users = [u for u in users if u.region_id == region_id or u.role.value == "owner"]
            doctors = [d for d in doctors if d.region_id == region_id]
            txs = [
                tx
                for tx in txs
                if (tx.from_user is not None and tx.from_user.region_id == region_id)
                or (tx.to_user is not None and tx.to_user.region_id == region_id)
                or (tx.to_doctor is not None and tx.to_doctor.region_id == region_id)
            ]
        if rep_id is not None:
            users = [u for u in users if u.id == rep_id]
            txs = [tx for tx in txs if tx.from_user_id == rep_id or tx.to_user_id == rep_id]

        inflow = sum(tx.amount for tx in txs if tx.kind == BallTxKind.MINT and tx.status == BallTxStatus.ACCEPTED)
        transferred = sum(
            tx.amount for tx in txs if tx.kind == BallTxKind.TRANSFER and tx.status == BallTxStatus.ACCEPTED
        )
        deducted = sum(tx.amount for tx in txs if tx.kind == BallTxKind.SALE_DEDUCT)

        return web.json_response(
            {
                "balances": {
                    "users": [
                        {
                            "name": u.full_name,
                            "role": u.role.value,
                            "region": u.region.name if u.region else None,
                            "balance": int(u.ball_balance or 0),
                        }
                        for u in users
                    ],
                    "doctors": [
                        {
                            "name": d.full_name,
                            "region": d.region.name if d.region else None,
                            "balance": int(d.ball_balance or 0),
                        }
                        for d in doctors
                    ],
                },
                "turnover": {"minted": inflow, "transferred": transferred, "deducted": deducted},
                "transactions": [
                    {
                        "date": str(tx.created_at)[:16],
                        "kind": tx.kind.value,
                        "status": tx.status.value,
                        "amount": tx.amount,
                        "from": tx.from_user.full_name if tx.from_user else None,
                        "to": tx.to_user.full_name
                        if tx.to_user
                        else (tx.to_doctor.full_name if tx.to_doctor else None),
                    }
                    for tx in txs[:200]
                ],
            }
        )


def create_webapp() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/api/meta", api_meta)
    app.router.add_get("/api/summary", api_summary)
    app.router.add_get("/api/ball", api_ball)
    return app
