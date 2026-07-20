from __future__ import annotations

"""Analitika web-paneli (aiohttp) — owner / TOP menejer / product menejer uchun.

Barcha /api/* endpointlar `token` query-parametri bilan himoyalangan
(app/webapp/auth.py). Ma'lumotlar davr/region/rep filtrlariga ko'ra qaytadi."""

import hmac
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from aiohttp import web
from sqlalchemy import select

from app.db.models import BallTxKind, BallTxStatus, Role, User
from app.db.repositories import (
    ball_balances_overview,
    list_all_drugs,
    doctors_ball_overview,
    ball_transactions_in_period,
    list_regions,
    list_sellers,
    sales_item_rows,
)
from app.db.session import AsyncSessionLocal
from app.webapp.auth import make_session, parse_session, parse_token

STATIC_DIR = Path(__file__).resolve().parent / "static"

WEBAPP_ROLES = {Role.OWNER, Role.TOP_MANAGER, Role.PRODUCT_MANAGER}
logger = logging.getLogger(__name__)


def _num(value) -> float | int:
    if isinstance(value, Decimal):
        return float(value)
    return value


async def _user_by_id(session, user_id: int | None) -> User | None:
    if user_id is None:
        return None
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active or user.role not in WEBAPP_ROLES:
        return None
    return user


async def _auth_user(request: web.Request, session) -> User | None:
    """Ma'lumot endpointlari — FAQAT tasdiqlangan SESSIYA (sid) qabul qilinadi.

    Havoladagi `token` o'zi yetarli emas: 2FA kodini kiritmasa `sid` bo'lmaydi."""
    return await _user_by_id(session, parse_session(request.query.get("sid")))


async def _link_user(request: web.Request, session) -> User | None:
    """Havola (link) token bilan aniqlash — faqat kod so'rash/tasdiqlash uchun."""
    return await _user_by_id(session, parse_token(request.query.get("token")))


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
        drugs = await list_all_drugs(session)
        return web.json_response(
            {
                "user": {"name": user.full_name, "role": user.role.value},
                "regions": [{"id": r.id, "name": r.name} for r in regions],
                "drugs": [{"id": d.id, "name": d.name} for d in drugs],
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
        drug_id = _int_or_none(request.query.get("drug_id"))

        rows = await sales_item_rows(
            session, start=start, end=end, region_id=region_id, rep_id=rep_id, drug_id=drug_id
        )

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


async def api_doctors(request: web.Request) -> web.Response:
    """Doktorlar kategoriyasi (A/B/C) + savdo qaytishи statистикаси."""
    async with AsyncSessionLocal() as session:
        user = await _auth_user(request, session)
        if user is None:
            return web.json_response({"error": "unauthorized"}, status=401)
        rows = await doctors_ball_overview(session, user)
        region_id = _int_or_none(request.query.get("region_id"))
        if region_id is not None:
            rows = [r for r in rows if r.get("region_id") == region_id or user.role.value == "owner"]
        # ЛПУ ro'yxati (filtr ochilувчиси uchun) — filtrdan OLDIN, region ko'lamидаги hammasи.
        lpus = sorted(
            {(r["lpu_id"], r["lpu"]) for r in rows if r.get("lpu_id")}, key=lambda x: (x[1] or "")
        )
        lpu_id = _int_or_none(request.query.get("lpu_id"))
        if lpu_id is not None:
            rows = [r for r in rows if r.get("lpu_id") == lpu_id]
        category = (request.query.get("category") or "").strip().upper()
        if category in {"A", "B", "C"}:
            rows = [r for r in rows if r["category"] == category]
        counts = {"A": 0, "B": 0, "C": 0}
        for r in rows:
            counts[r["category"]] = counts.get(r["category"], 0) + 1
        return web.json_response({
            "counts": counts,
            "doctors": rows,
            "lpus": [{"id": i, "name": n} for i, n in lpus],
        })


# ==================== 2FA: bir martalik kod (Telegram orqali) ====================
# Kodlar xotirada (bitta process): user_id -> {code, exp, attempts, last_sent}.
# Restartda yo'qoladi — foydalanuvchi qaytadan kod so'raydi (sessiya esa imzoli, omon qoladi).
_pending_codes: dict[int, dict] = {}
CODE_TTL = 300          # kod 5 daqiqa amal qiladi
CODE_RESEND_MIN = 30    # qayta yuborishlar orasida kamida 30 soniya
CODE_MAX_ATTEMPTS = 5   # bitta kodga ko'pi bilan 5 urinish


async def api_request_code(request: web.Request) -> web.Response:
    """Havola egasining Telegram'iga 6 xonali kirish kodini yuboradi."""
    async with AsyncSessionLocal() as session:
        user = await _link_user(request, session)
    if user is None:
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
    if not user.telegram_id:
        return web.json_response({"ok": False, "error": "no_telegram"})

    now = int(time.time())
    entry = _pending_codes.get(user.id)
    if entry and now - entry["last_sent"] < CODE_RESEND_MIN:
        return web.json_response({"ok": False, "error": "too_soon", "wait": CODE_RESEND_MIN - (now - entry["last_sent"])})

    code = f"{secrets.randbelow(1_000_000):06d}"
    _pending_codes[user.id] = {"code": code, "exp": now + CODE_TTL, "attempts": 0, "last_sent": now}

    bot = request.app.get("bot")
    if bot is None:
        return web.json_response({"ok": False, "error": "bot_unavailable"}, status=500)
    try:
        await bot.send_message(
            user.telegram_id,
            f"🔐 <b>Web панель кириш коди:</b> <code>{code}</code>\n"
            f"5 дақиқа амал қилади. Уни ҳеч кимга берманг.",
        )
    except Exception as exc:  # bot bloklangan / chat topilmadi
        logger.warning("2FA code send failed (user=%s): %s", user.id, exc)
        return web.json_response({"ok": False, "error": "send_failed"})
    return web.json_response({"ok": True})


async def api_verify_code(request: web.Request) -> web.Response:
    """Kod to'g'ri bo'lsa — muddatли SESSIYA (sid) beradi."""
    async with AsyncSessionLocal() as session:
        user = await _link_user(request, session)
    if user is None:
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

    code = (request.query.get("code") or "").strip()
    entry = _pending_codes.get(user.id)
    now = int(time.time())
    if entry is None or entry["exp"] < now:
        _pending_codes.pop(user.id, None)
        return web.json_response({"ok": False, "error": "expired"})
    entry["attempts"] += 1
    if entry["attempts"] > CODE_MAX_ATTEMPTS:
        _pending_codes.pop(user.id, None)
        return web.json_response({"ok": False, "error": "too_many"})
    if not code or not hmac.compare_digest(code, entry["code"]):
        return web.json_response({"ok": False, "error": "wrong", "left": CODE_MAX_ATTEMPTS - entry["attempts"]})

    _pending_codes.pop(user.id, None)  # bir martalik — ishlatildi
    return web.json_response({"ok": True, "sid": make_session(user.id)})


def create_webapp(bot=None) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", index)
    app.router.add_get("/api/request-code", api_request_code)
    app.router.add_get("/api/verify-code", api_verify_code)
    app.router.add_get("/api/meta", api_meta)
    app.router.add_get("/api/summary", api_summary)
    app.router.add_get("/api/ball", api_ball)
    app.router.add_get("/api/doctors", api_doctors)
    return app
