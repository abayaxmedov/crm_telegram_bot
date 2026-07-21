from __future__ import annotations

"""Ovozni matnga o'girish (STT) — ElevenLabs Scribe.

Ovozli hisobot yuborilganda FON REJIMIDA chaqiriladi (hisobot saqlanishini
to'smaydi). Natija `daily_reports.voice_text` ga yoziladi.

Provayder ALMASHTIRILADIGAN qilib ajratilgan: faqat shu fayl o'zgaradi, keyinchalik
Aisha yoki boshqa xizmatga o'tish uchun `transcribe()` ni almashtirish yetarli.

Kalit (ELEVENLABS_API_KEY) bo'lmasa — hech narsa qilmaydi (None qaytaradi),
ya'ni funksiya kalit qo'yilmaguncha xavfsiz "o'chiq" turadi.
"""

import logging

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)

_ELEVENLABS_URL = "https://api.elevenlabs.io/v1/speech-to-text"
_TIMEOUT = aiohttp.ClientTimeout(total=120)  # uzun ovoz + tarmoq uchun


async def transcribe(audio: bytes, filename: str = "voice.ogg", content_type: str = "audio/ogg") -> str | None:
    """Ovoz baytlarini matnga o'giradi. Xato/kalitsiz bo'lsa None.

    Til AVTOMATIK aniqlanadi (o'zbek/rus aralash bo'lishi mumkin — majburlamaymiz).
    Telegram ovozi OGG/Opus formatida keladi; ElevenLabs Scribe uni qabul qiladi."""
    if not settings.stt_enabled():
        return None
    if not audio:
        return None

    form = aiohttp.FormData()
    form.add_field("model_id", settings.elevenlabs_stt_model)
    form.add_field("file", audio, filename=filename, content_type=content_type)

    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.post(
                _ELEVENLABS_URL,
                headers={"xi-api-key": settings.elevenlabs_api_key},
                data=form,
            ) as resp:
                if resp.status != 200:
                    body = (await resp.text())[:300]
                    logger.warning("STT failed: HTTP %s — %s", resp.status, body)
                    return None
                data = await resp.json()
    except Exception as exc:  # tarmoq/timeout
        logger.warning("STT request error: %s", exc)
        return None

    text = (data.get("text") or "").strip()
    return text or None
