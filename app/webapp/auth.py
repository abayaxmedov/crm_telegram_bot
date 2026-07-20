from __future__ import annotations

"""Web-panel autentifikatsiyasi — imzolangan (HMAC-SHA256) muddatli tokenlar.

Ikki xil token:
  • LINK token (`token=`) — botdagi havolada bo'ladi; kim ekanini bildiradi, lekin
    o'zi kirishga YETARLI EMAS. Faqat "kirish kodini shu odamga yuborish" uchun.
  • SESSION token (`sid=`) — Telegram'ga yuborilgan bir martalik kod TO'G'RI
    kiritilgandan keyin beriladi. Ma'lumot endpointlari FAQAT shuni qabul qiladi.

Shu tariqa havola begonaga tushsa ham, u kodni (haqiqiy egasining Telegram'idan)
ololmaydi — demak sessiya ololmaydi va ma'lumotni ko'ra olmaydi.

Format: base64url("user_id:expires_unix") + "." + hex(hmac[:32]).
Secret bot tokenidan hosil qilinadi — alohida kalit saqlash shart emas."""

import base64
import hashlib
import hmac
import time

from app.config import settings

LINK_TTL_SECONDS = 24 * 3600      # havola muddati (kod so'rash uchun)
SESSION_TTL_SECONDS = 6 * 3600    # tasdiqdan keyingi sessiya muddati

# Eski kod bilan moslik uchun nom.
TOKEN_TTL_SECONDS = LINK_TTL_SECONDS


def _secret(kind: str) -> bytes:
    return hashlib.sha256(f"webapp-{kind}:{settings.bot_token}".encode()).digest()


def _sign(payload: str, kind: str) -> str:
    return hmac.new(_secret(kind), payload.encode(), hashlib.sha256).hexdigest()[:32]


def _make(user_id: int, ttl_seconds: int, kind: str) -> str:
    payload = f"{user_id}:{int(time.time()) + ttl_seconds}"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{encoded}.{_sign(payload, kind)}"


def _parse(token: str | None, kind: str) -> int | None:
    """Token to'g'ri va muddati o'tmagan bo'lsa user_id, aks holda None."""
    if not token or "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = base64.urlsafe_b64decode(padded.encode()).decode()
    except Exception:
        return None
    if not hmac.compare_digest(_sign(payload, kind), signature):
        return None
    try:
        user_id_raw, expires_raw = payload.split(":", 1)
        user_id, expires = int(user_id_raw), int(expires_raw)
    except ValueError:
        return None
    if expires < int(time.time()):
        return None
    return user_id


# ---- LINK token (havola) ----
def make_token(user_id: int, ttl_seconds: int = LINK_TTL_SECONDS) -> str:
    return _make(user_id, ttl_seconds, "auth")


def parse_token(token: str | None) -> int | None:
    return _parse(token, "auth")


# ---- SESSION token (2FA tasdiqdan keyin) ----
def make_session(user_id: int, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    return _make(user_id, ttl_seconds, "session")


def parse_session(token: str | None) -> int | None:
    return _parse(token, "session")
