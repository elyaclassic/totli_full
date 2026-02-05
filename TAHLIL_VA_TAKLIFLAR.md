# Loyiha chuqur tahlili — Ishlab chiqarish va biznes avtomatlashtirish

**Sana:** 2026-02-05  
**Maqsad:** Qanday qo‘shimcha ishlar kerakligi va ularni qanday tartibda qilish to‘g‘ri bo‘lishi.

---

## Hozirgi holat (qisqacha)

| Bo‘lim | Holat |
|--------|--------|
| **Auth, login, session** | ✅ Ishlaydi (bcrypt, middleware) |
| **Ma’lumotnomalar** (ombor, birlik, kategoriya, narx turlari, bo‘lim, yo‘nalish, xodimlar, foydalanuvchilar) | ✅ CRUD, import/export |
| **Tovarlar** | ✅ Ro‘yxat, qo‘shish, tahrir, o‘chirish, shtrix kod, rasmlar |
| **Sotuvlar** | ✅ Yangi sotuv, tahrir, tasdiq, o‘chirish (draft), narx turi |
| **Tovar kirimi (Purchase)** | ✅ Ro‘yxat, yangi, tahrir, tasdiq, revert |
| **Ombor qoldiqlari** | ✅ Ro‘yxat (warehouse list) |
| **Ishlab chiqarish** | ✅ Retseptlar, buyurtmalar, materiallar tahrir, complete/revert |
| **Agentlar, yetkazib berish, xarita** | ✅ Ro‘yxat, GPS API (agent/driver), xarita |
| **Hisobotlar** | ✅ Savdo, qoldiq, qarzdorlik (faqat ko‘rsatish) |
| **Dashboardlar** | ✅ Executive, sales, warehouse, production, delivery, agent; live data, executive export |
| **PWA / mobil API** | ✅ Agent/driver login, location, orders, partners |

---

## Kamchiliklar va bo‘shliqlar

1. **Ombor harakati** — `/warehouse/movement` route bor, lekin `warehouse/movement.html` shabloni yo‘q → sahifa ochilganda 500 xato.
2. **Uskunalar (Machine)** — Bazada `machines` jadvali va `machine_management.py` (CRUD) bor, lekin `main.py` ga ulanmagan. Production dashboard da faqat placeholder (0 yoki test ma’lumot).
3. **Avtomatik bildirishnomalar** — Kam qolgan tovar uchun `create_low_stock_notification` funksiyasi bor, lekin kirim/sotuv/production tasdiqlanganda avtomatik chaqirilmaydi.
4. **Hisobotlar eksport** — Faqat Executive dashboard Excel export bor. Savdo, qoldiq, qarzdorlik hisobotlarida Excel/PDF eksport yo‘q.
5. **PWA rejasi** — Lokatsiya yuborish intervali, offline sync, buyurtma qabul qilish API hali to‘liq integratsiya qilinmagan.
6. **Bosh sahifa bildirishnomalar** — "Bugun tug‘ilgan kunlar", "Muddati o‘tgan qarzlar" — backend da real hisoblash yo‘q (0 ko‘rsatiladi).
7. **Ishlab chiqarish va uskuna** — Production buyurtmaga qaysi uskuna (machine) va operator biriktirilgani saqlanmaydi; uskuna holati (band/bo‘sh) ishlab chiqarish bilan bog‘lanmagan.
8. **Reja (cron/scheduler)** — Kunlik yoki vaqt bo‘yicha vazifalar yo‘q: masalan, kam qolgan tovar tekshiruvi, muddati o‘tgan qarz eslatmasi.

---

## TAKLIFLAR — Siz tanlaysiz, men bajaraman

Quyidagi bandlardan keraklilarini raqamini yozing (masalan: 1, 3, 5). Shunchalarini amalga oshiraman.

---

### 1. Ombor harakati sahifasi (movement)
- **Muammo:** `warehouse/movement.html` yo‘q, 500 xato.
- **Qilish:** `warehouse/movement.html` shablonini yaratish — mahsulot/ombor bo‘yicha kirim-chiqim (purchase confirm, sale confirm, production complete) jadvali yoki oddiy “harakatlar ro‘yxati” sahifasi.
- **Natija:** Ombor harakati sahifasi ishlaydi, xato yo‘qoladi.

---

### 2. Uskunalar (Machine) moduli — CRUD va menyu
- **Muammo:** Machine modeli va `machine_management.py` bor, lekin hech qanday sahifa/route yo‘q.
- **Qilish:** `/info/machines` (yoki `/production/machines`) — ro‘yxat, qo‘shish, tahrir, o‘chirish (yoki faqat “faol emas”). Menyuda “Uskunalar” bo‘limi.
- **Natija:** Uskunalar boshqariladi, production dashboard da haqiqiy ma’lumotdan foydalanish mumkin.

---

### 3. Avtomatik “kam qolgan tovar” bildirishnomalari
- **Muammo:** Tovar kirimi/sotuv/production tasdiqlanganda qoldiq kamayadi, lekin bildirishnoma avtomatik yaratilmaydi.
- **Qilish:** Purchase confirm, sales confirm, production complete qilganda har bir ombor mahsuloti uchun `quantity < product.min_stock` bo‘lsa `create_low_stock_notification` chaqirish.
- **Natija:** Kam qolgan tovarlar haqida tizimda bildirishnoma paydo bo‘ladi.

---

### 4. Hisobotlar uchun Excel eksport
- **Muammo:** Reports/sales, reports/stock, reports/debts — faqat HTML, eksport yo‘q.
- **Qilish:** Har bir hisobot uchun “Excelga yuklab olish” tugmasi va endpoint (masalan `/reports/sales/export`, `/reports/stock/export`, `/reports/debts/export`).
- **Natija:** Savdo, qoldiq va qarzdorlik hisobotlarini Excel da olish mumkin.

---

### 5. Bosh sahifa bildirishnomalari — real ma’lumot
- **Muammo:** “Bugun tug‘ilgan kunlar”, “Muddati o‘tgan qarzlar” hozir 0.
- **Qilish:** Employee da `birth_date` (yoki mavjud sana maydoni) bo‘lsa — bugun tug‘ilganlar soni; Partner/Order da qarz va muddat bo‘yicha “muddati o‘tgan” hisoblash va bosh sahifada shu raqamlarni ko‘rsatish.
- **Eslatma:** Agar Employee da tug‘ilgan kun maydoni yo‘q bo‘lsa, avval jadvalga ustun qo‘shish kerak.
- **Natija:** Bosh sahifada mazmunli raqamlar.

---

### 6. Ishlab chiqarish buyurtmasiga uskuna va operator
- **Muammo:** Production da qaysi uskuna va operator ishlatilgani saqlanmaydi.
- **Qilish:** `Production` jadvaliga `machine_id`, `operator_id` (yoki mavjud bo‘lsa ishlatish). Production “yangi buyurtma” / “tahrir” sahifasida uskuna va operator tanlash. Dashboard da “qaysi uskuna band” ko‘rsatish (ixtiyoriy).
- **Natija:** Ishlab chiqarish va uskunalar bog‘lanadi, keyinchalik hisobotlar aniqroq bo‘ladi.

---

### 7. PWA: lokatsiya yuborish va offline
- **Muammo:** PWA rejasida “har 5 daqiqada lokatsiya”, “offline sync” yozilgan, amalda to‘liq yo‘q.
- **Qilish:** PWA frontend da (masalan `app/static/pwa/`) interval orqali lokatsiya yuborish (har N daqiqada). Ixtiyoriy: Service Worker va LocalStorage orqali offline rejimda saqlash va keyin sync.
- **Natija:** Agent/haydovchi ilovasi vaqtida lokatsiya yuboradi, offline ishlash yaxshilanadi.

---

### 8. Reja (scheduler) — kunlik vazifalar
- **Muammo:** Vaqt bo‘yicha avtomatik vazifalar yo‘q.
- **Qilish:** APScheduler (yoki oddiy background thread) bilan kunlik: (a) barcha omborlar uchun `quantity < min_stock` tekshiruv va kerak bo‘lsa bildirishnoma; (b) muddati o‘tgan qarzlar uchun bildirishnoma. Server ishga tushganda scheduler ishga tushadi.
- **Natija:** Har kuni yoki har N soatda kam qolgan tovar va muddati o‘tgan qarzlar haqida eslatma.

---

### 9. main.py ni router larga bo‘lish
- **Muammo:** `main.py` 5000+ qator, barcha route lar bitta faylda.
- **Qilish:** `app/routes/` ostida `auth.py`, `products.py`, `sales.py`, `purchases.py`, `production.py`, `reports.py`, `info.py`, `agents.py`, `delivery.py` va h.k. — har biri o‘z router i. `main.py` da faqat `app.include_router(...)`.
- **Natija:** Kod tartibli, yangi funksiyalar qo‘shish oson.

---

### 10. CSRF token (xavfsizlik)
- **Muammo:** Formalar uchun CSRF himoya yo‘q.
- **Qilish:** Barcha POST formalarga yashirin CSRF token qo‘shish, serverda tekshirish (middleware yoki dependency).
- **Natija:** So‘rovlarni boshqa saytdan yuborish (CSRF hujumi) qiyinlashadi.

---

## Qisqa ustunvorlik tavsiyasi

- **Tez foyda:** 1 (ombor harakati — xato tuzatish), 3 (avtomatik bildirishnoma), 4 (hisobotlar eksport).
- **Ishlab chiqarish:** 2 (uskunalar CRUD), 6 (production + machine/operator).
- **Mobil va avtomatlashtirish:** 7 (PWA), 8 (scheduler).
- **Tuzilma va xavfsizlik:** 9 (router lar), 10 (CSRF).

---

**Qaysi raqamlarni bajarishim kerak?**  
Javobingizni yozing (masalan: `1, 2, 3, 4`), shu bandlarni tartib bilan bajaraman.
