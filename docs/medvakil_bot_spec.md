# test3640bot — o'rganilgan spetsifikatsiya (Медпредставитель roli)

Bu hujjat `test3640bot` ni jonli o'rganib chiqib tuzildi. Maqsad — bizning botni
shu mantiqqa moslashtirish uchun blueprint. Bu yerda faqat **Медпредставитель**
(bizda: MANAGER → «Медвакил») roli oqimi. Qolgan rollar (admin/owner) keyin qo'shiladi.

> Eslatma: Barcha oqimlar jonli botda ko'rildi. Real transaksiyalar bajarilmadi
> (masalan врачга pul chiqarish, склад buyurtmasini yuborish — tasdiqlanmadi).

## Asosiy menyu (reply keyboard)

`/start` → «Меню медпредставителя:». Tugmalar (2 ustun):

```
👨‍⚕️ Врачи            💊 Аптеки
🛍 Продажи            📦 Заявка на склад
📖 Дневник            💰 Финансы
        💰 Моя зарплата
```

Foydalanuvchi profili sarlavhasi: `Медпредставитель: <FIO>`, `Регион: <город>, <район>`.

---

## 1. 👨‍⚕️ Врачи (Vrachlar)

«Управление врачами:» → inline:
- **➕ Добавить врача** → birinchi so'rov: «Введите ФИО врача:» (keyin qo'shimcha maydonlar).
- **👤 Мои врачи** — rep o'ziga biriktirilgan vrachlar ro'yxati.

Vrachning muhim atributi: **bonus balansi** (Продажи orqali to'planadi, Финансы orqali
to'lanadi). Skrinshotda: «Баланс бонусов врача: 470.00 руб.».

## 2. 💊 Аптеки (Aptekalar)

«Управление аптеками:» → inline:
- **➕ Добавить аптеку** → «Введите название аптеки:» (keyin: manzil, ИНН, mas'ul shaxs...).
- **👤 Мои аптеки** — rep aptekalari ro'yxati.

Aptekada: **ИНН**, **филиал** (masalan «мунавара (Филиал: 1)»), va **договорлар** (quyida).

## 3. 🛍 Продажи (Sotuv / retsept qayd etish) — YADRO

Oqim:
1. «Выберите аптеку, в которой была совершена продажа:» → apteka (yoki filial) tanlanadi.
2. «Выберите врача, выписавшего рецепт:» → vrach tanlanadi.
3. «Выберите проданный препарат:» → preparat (yonida **qoldiq**: «Остаток: 33 шт»).
4. «Введите количество проданных упаковок:» → son kiritiladi (masalan 3).
5. «📦 Текущая корзина рецепта: 1. TEST PREPORAT — 3 шт.» → **➕ Добавить ещё препарат** / **✅ Завершить**.
6. Yakun: «✅ Успешно! Рецепт зарегистрирован. Врачу TEST VRACH начислен **бонус: 30**.
   📋 Детализация: 1. TEST PREPORAT — 3 шт. × 10 = 30».

**Muhim:** har preparatning **vrach bonusi stavkasi** bor (bu yerda ×10 = 1 upakovka uchun 10).
Sotuv = retsept (savat) → vrachga bonus hisoblanadi + preparat qoldig'i kamayadi +
bu sotuv KPI (zarplata) uchun **факт** bo'lib qo'shiladi.

## 4. 📦 Заявка на склад (Sklad buyurtmasi)

Oqim:
1. «Введите ИНН или название аптеки для поиска:» → apteka qidiriladi (ИНН yoki nom bo'yicha).
2. «Выберите договор или запросите новый:» → mavjud **Договор № … от <sana>** tanlanadi
   yoki **➕ Запросить новый договор**.
3. «Выберите препарат для добавления в заявку:» → preparat tanlanadi.
4. (Keyin: son, yana qo'shish, yakunda buyurtma yuboriladi.)

**Muhim:** sklad buyurtmasi **договор (shartnoma)** asosida ishlaydi. Har aptekada bir
nechta договор bo'lishi mumkin (raqam + sana). Yangi договор so'rash imkoni bor.

## 5. 📖 Дневник (Tashriflar kundaligi)

«📓 Дневник визитов медпредставителя» → inline:
- **✍️ Новая запись** → «📍 Для создания новой записи отправьте вашу геолокацию (Live или
  статическую)…» — **geolokatsiya majburiy** (tashrif joyda ekani isboti). Tugmalar:
  «📍 Отправить геолокацию», «❌ Отмена».
- **🔍 Поиск записей**
- **📋 Последние 5 записей**

**Muhim:** kundalik yozuvi geolokatsiyaga bog'langan (visit tracking). Alohida «test_location»
chatda «Рабочая смена успешно завершена. Сбор геолокации…» ko'rindi — ish smenasi va
geolokatsiya yig'ish ham bor.

## 6. 💰 Финансы

Sarlavha: `Медпредставитель`, `Регион`, `💰 Ваш текущий баланс под отчёт: X руб.`
(«под отчёт» = admin bergan hisobot puli / avans). Tugmalar:
- **💸 Выдать деньги врачу**:
  1. «Выберите врача для выплаты бонуса (Ваш баланс: X руб.):» → vrach.
  2. «Выбран врач: … Баланс бонусов врача: 470.00 руб. Ваш доступный баланс: X руб.
     Введите сумму выплаты:»
  3. Summa kiritiladi → mablag' tekshiriladi. Yetmasa: «Недостаточно средств на вашем
     балансе! Доступно: X руб.». Yetsa: to'lanadi (rep «под отчёт» balansi kamayadi,
     vrach bonus balansi kamayadi).
- **💵 Вернуть деньги админу**: ortgan «под отчёт»ni adminga qaytarish. Balans 0 bo'lsa:
  «Ваш баланс равен 0 руб. Возврат средств невозможен.»
- **🔄 Главное меню**.

**Pul aylanishi:** admin → rep (под отчёт) → vrach (bonus to'lovi) / rep → admin (qaytarish).

## 7. 💰 Моя зарплата (KPI asosida avtomatik)

`💰 Моя зарплата за <oy>`, `🧑 ФИО`. Keyin **har preparat bo'yicha KPI**:

```
💊 TEST PREPORAT (1 мес.)
 • Период: 01.07.2026 – 31.07.2026
 • План: 200 упак. | Факт: 3 упак.
 • Выполнение: 1.5% (округлено до: 0%)
 • Накопленный KPI Бонус: 0.00 руб.
 • Выплата в этом месяце: 0.00 руб.
```

So'ng:
```
🧮 Финансовый расчёт за месяц:
 • KPI Бонусы (1 мес): 0.00 руб.
 • KPI Бонусы (3 мес): 0.00 руб.
 • KPI Бонусы (6 мес): 0.00 руб.
💰 Итого к выплате: 0.00 руб.
*Зарплата рассчитывается в режиме реального времени на основе внесённых продаж.
```

**Muhim:** zarplata qo'lda kiritilmaydi — **plan vs fakt** (sotuvlardan) bo'yicha
avtomatik hisoblanadi. Har preparatda plan (upakovka), davr (1/3/6 oy), bajarilish %,
va shu %ga qarab KPI bonus. Umumiy = 1/3/6-oylik KPI bonuslar yig'indisi. Real vaqt.

---

## Bizning hozirgi bot bilan farq (nima qo'shilishi kerak)

| Blok | Hozirgi bizda | test3640bot (kerak) |
|------|---------------|---------------------|
| Rol | Manager/Operator/Assistant... | **Медвакил** (+region, +под отчёт balans) |
| Vrach | ism, tel, kategoriya | + **bonus balansi** |
| Apteka | nom, tel, mas'ul | + **ИНН**, **филиал**, **договорлар** |
| Preparat | ❌ yo'q | **bor**: nom, qoldiq, vrach-bonus stavka, KPI plan/stavka |
| Sotuv (Продажи) | ❌ yo'q | apteka+vrach+preparatlar → vrach bonusi, qoldiq− |
| Заявка на склад | oddiy «zayavka» | apteka+**договор**+preparatlar |
| Дневник | matn/voice hisobot | **geolokatsiyali** visit + smena |
| Финансы | owner: kirim/chiqim | под отчёт, vrachga to'lov, adminga qaytarish |
| Zarplata | qo'lda (base+bonus−jarima) | **KPI avtomatik** (plan/fakt, 1/3/6 oy) |

## Taklif etilgan bosqichlar (rep roli uchun)

1. **Ma'lumot modeli:** User(region, balans), Doctor(bonus_balance), Pharmacy(inn, filial),
   Contract(договор), Drug(qoldiq, bonus_rate, kpi_plan/stavka), Sale/Recipe, WarehouseRequest,
   VisitDiary(geo), FinanceLedger (под отчёт / to'lov / qaytarish).
2. **Продажи** oqimi (yadro — bonus va KPI shu yerdan oziqlanadi).
3. **Финансы** (под отчёт, vrachga to'lov, qaytarish).
4. **Моя зарплата** KPI hisoblagichi.
5. **Заявка на склад** (договор asosida).
6. **Дневник** (geolokatsiya).
7. Vrач/Апteka CRUDlarini kengaytirish (bonus balans, ИНН, филиал, договор).

> Admin/owner tomoni (planlar qo'yish, preparat/договор boshqaruvi, под отчёт berish)
> — keyingi rollar ko'rsatilgach aniqlashtiriladi.

---

## ✅ Amalga oshirildi (as-built)

Медвакил (bizda `MANAGER` roli) uchun 7 bo'lim ham qurildi va **iккала tilda** (Ўзбекча
кирилл + Русский) ishlaydi. Rol menyusi test3640bot uslubida almashtirildi.

**Yangi/o'zgargan fayllar:**
- `app/db/models.py` — Drug, Contract, Sale/SaleItem, WarehouseRequest/Item, VisitDiary,
  RepPayment; User(region, balance), Doctor(bonus_balance), Pharmacy(inn, filial).
- `app/db/session.py` — yangi ustunlar uchun yengil migratsiya (avtomatik).
- `app/i18n.py` — ~90 yangi kalit (uz_cyrl+ru), oy nomlari.
- `app/handlers/filters.py` — `RoleFilter` (rol bo'yicha handler tanlash).
- `app/handlers/sales.py` — Продажи; `warehouse.py` — Заявка; `diary.py` — Дневник;
  `rep_finance.py` — Финансы (под отчёт) + Моя зарплата (KPI).
- `app/services/kpi.py` — KPI hisoblagich.
- `app/keyboards/reply.py` — Медвакил menyusi + inline builderlar.
- `scripts/seed_demo.py` — demo препарат/договор (test uchun).

**Ishlash tartibi:** Медвакил `Финансы`/`Моя зарплата` tugmalari owner bilan bir xil
matnda, lekin `RoleFilter` orqali MANAGER → rep oqimi, owner → eski oqim. Boshqa rollar
o'zgarmadi.

### ⚠️ Tasdiqlash kerak bo'lgan taxminlar (skriptdan aniq bo'lmagani uchun)

1. **Vrach bonusi** = `sotilgan_upakovka × препарат.doctor_bonus_per_pack`. (Seed: ×10.)
2. **KPI zarplata formulasi** (созланадиган):
   `выполнение% = факт/план×100` → `яхлитланган% = floor(%/10)×10` (макс 100) →
   `бонус = препарат.kpi_bonus_full × яхлитланган%/100`. Masalan 1.5% → 0% → 0 (скриншотга мос).
   Ставкалар ҳар препаратда сақланади (`kpi_plan_qty`, `kpi_period_months`, `kpi_bonus_full`).
3. **Давр** (1/3/6 ой): факт жорий ойдан (period-1) ой орқага ойнада ҳисобланади.
4. **«Под отчёт» баланс** ҳозирча seed/repo орқали берилади (`issue_podotchet`). Ботдан
   бериш — admin роли билан қўшилади.
5. **Заявка на склад** буюртмани `status=new` билан сақлайди (складни тўлдириш — admin томони).

Бу қийматларни ва формулани реал ботдагидек аниқ айтсангиз, дарҳол мослайман.

### Test qilish
```bash
python scripts/seed_demo.py           # demo препарат/договор
# foydalanuvchini MANAGER roli qiling (owner /admin orqali user yaratadi)
```
