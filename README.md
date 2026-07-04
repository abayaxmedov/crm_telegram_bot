# CRM Telegram Bot

Yopiq Telegram CRM bot: vrachlar, aptekalar, kundalik hisobotlar, zayavkalar, finans va zarplata jarayonlari.

## Ishga tushirish

1. `.env` faylida `BOT_TOKEN`, `OWNER_IDS` va `DATABASE_URL` borligini tekshiring.
2. Docker orqali ishga tushiring:

```bash
docker compose up --build
```

Bot start vaqtida DB jadvallarini yaratadi va `89245245`, `6087841574` Telegram ID larini `owner` qilib seed qiladi.

## Asosiy imkoniyatlar

- Yopiq kirish: begona user `/start` bossa javob qaytmaydi.
- Invite token: owner yoki manager user yaratadi, link orqali Telegram ID bazaga biriktiriladi.
- Role-based menu: owner, manager, operator, operator yordamchisi, vrach, apteka.
- Ikki tilli interfeys: **Ўзбекча (кирилл)** va **Русский**. Har bir foydalanuvchi `/start` da yoki menyudagi `🌐 Тил / Язык` tugmasi (`/language`) orqali tilni tanlaydi; barcha xabar, tugma va rasm caption'lari tanlangan tilda chiqadi. Tanlov `users.language` ustunida saqlanadi.
- Vrach/apteka kataloglari.
- Yozma va voice kundalik hisobotlar.
- Zayavka yaratish va status boshqarish.
- Owner uchun finans operatsiyalari.
- Zarplata yozuvlari va userga o'z oyligini ko'rish.
- Javoblar lokal rasmlar va WebP stickerlar bilan bezatiladi.

## Lokal assets

Rasm va stickerlar har til uchun alohida papkada saqlanadi: `assets/photos/<lang>/` va
`assets/stickers/<lang>/` (`lang` = `uz_cyrl` yoki `ru`). Zamonaviy, to'q korporativ uslub.
Ularni qayta generatsiya qilish:

```bash
python scripts/generate_assets.py
```

