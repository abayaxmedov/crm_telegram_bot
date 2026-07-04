from __future__ import annotations

"""Ekran <-> media fayl xaritalari.

Barcha foydalanuvchiga ko'rinadigan matnlar app/i18n.py da. Bu yerda faqat
qaysi ekran uchun qaysi rasm/stiker ishlatilishi va sarlavha tarjima kaliti.
"""

PHOTO_BY_SCREEN = {
    "welcome": "welcome.jpg",
    "menu": "menu.jpg",
    "admin": "admin.jpg",
    "doctors": "doctors.jpg",
    "pharmacies": "pharmacies.jpg",
    "daily": "daily.jpg",
    "requests": "requests.jpg",
    "finance": "finance.jpg",
    "salary": "salary.jpg",
}

STICKER_BY_SCREEN = {
    "welcome": "welcome.webp",
    "admin": "admin.webp",
    "daily": "daily.webp",
    "done": "done.webp",
}

# Ekran -> i18n sarlavha kaliti (rasm caption uzun bo'lganda fallback sarlavha).
SCREEN_TITLE_KEYS = {
    "welcome": "title_welcome",
    "menu": "title_menu",
    "admin": "title_admin",
    "doctors": "title_doctors",
    "pharmacies": "title_pharmacies",
    "daily": "title_daily",
    "requests": "title_requests",
    "finance": "title_finance",
    "salary": "title_salary",
}
