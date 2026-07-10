from __future__ import annotations

"""Web-panel uchun imzolangan (HMAC-SHA256) muddatli token.

Format: base64url("user_id:expires_unix") + "." + hex(hmac[:32]).
Secret bot tokenidan hosil qilinadi — alohida kalit saqlash shart emas."""

import base64
import hashlib
import hmac
import time

from app.config import settings

TOKEN_TTL_SECONDS = 24 * 3600


def _secret() -> bytes:
    return hashlib.sha256(f"webapp-auth:{settings.bot_token}".encode()).digest()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def make_token(user_id: int, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    payload = f"{user_id}:{int(time.time()) + ttl_seconds}"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{encoded}.{_sign(payload)}"


def parse_token(token: str | None) -> int | None:
    """Token to'g'ri va muddati o'tmagan bo'lsa user_id, aks holda None."""
    if not token or "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = base64.urlsafe_b64decode(padded.encode()).decode()
    except Exception:
        return None
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        user_id_raw, expires_raw = payload.split(":", 1)
        user_id, expires = int(user_id_raw), int(expires_raw)
    except ValueError:
        return None
    if expires < int(time.time()):
        return None
    return user_id
