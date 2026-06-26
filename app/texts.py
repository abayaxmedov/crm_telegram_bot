from __future__ import annotations

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

SCREEN_TITLES = {
    "welcome": "CRM botga xush kelibsiz",
    "menu": "Asosiy menyu",
    "admin": "Admin panel",
    "doctors": "Vrachlar bo'limi",
    "pharmacies": "Aptekalar bo'limi",
    "daily": "Kundalik hisobot",
    "requests": "Zayavkalar",
    "finance": "Finans",
    "salary": "Moy zarplata",
}

BOT_DESCRIPTION = (
    "Dorixona, vrachlar, menejerlar, zayavkalar, kundaliklar, finans va zarplata "
    "jarayonlari uchun yopiq ichki CRM bot."
)
BOT_SHORT_DESCRIPTION = "Ichki CRM: vrachlar, aptekalar, kundalik, finans va zayavkalar."

WELCOME_TEXT = (
    "<b>Assalomu alaykum!</b>\n\n"
    "Siz kompaniyaning yopiq CRM botiga kirdingiz. Bu yerda rolingizga qarab "
    "vrachlar, aptekalar, kundalik hisobotlar, zayavkalar, finans va zarplata "
    "bo'limlari ochiladi.\n\n"
    "<i>Har bir amal bazaga yoziladi va owner tomonidan nazorat qilinadi.</i>"
)

MENU_TEXT = (
    "<b>Asosiy menyu</b>\n\n"
    "Kerakli bo'limni tanlang. Bot sizga faqat ruxsat berilgan funksiyalarni ko'rsatadi."
)

ADMIN_TEXT = (
    "<b>Admin panel</b>\n\n"
    "User yaratish invite-token orqali ishlaydi: avval role va ism kiritiladi, "
    "keyin bot maxsus havola beradi. Begona userlar /start bosganda javob olmaydi."
)

DOCTORS_TEXT = (
    "<b>Vrachlar bo'limi</b>\n\n"
    "Vrachning ism-familiyasi, telefon raqami, lokatsiyasi, sinfi/kategoriyasi "
    "va mas'ul menejer ma'lumotlari saqlanadi."
)

PHARMACIES_TEXT = (
    "<b>Aptekalar bo'limi</b>\n\n"
    "Apteka nomi, lokatsiya, telefon, mas'ul shaxs va biriktirilgan menejer "
    "bo'yicha yozuvlar yuritiladi."
)

DAILY_TEXT = (
    "<b>Kundalik</b>\n\n"
    "Menejerlar va xodimlar yozma yoki ovozli hisobot qoldirishi mumkin. "
    "Voice fayl Telegram file_id ko'rinishida bazada saqlanadi."
)

REQUESTS_TEXT = (
    "<b>Zayavkalar</b>\n\n"
    "Yangi zayavka yarating, statusini kuzating: yangi, jarayonda, bajarildi yoki bekor qilindi."
)

FINANCE_TEXT = (
    "<b>Finans</b>\n\n"
    "Kirim, chiqim, qarzdorlik va to'lovlar owner nazoratida saqlanadi."
)

SALARY_TEXT = (
    "<b>Moy zarplata</b>\n\n"
    "Oylik, bonus, jarima va yakuniy summa bo'yicha ma'lumotlar."
)

