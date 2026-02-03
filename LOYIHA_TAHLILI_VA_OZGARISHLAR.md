# Loyiha tahlili va so‘nggi o‘zgarishlar

**Sana:** 2026-02-02  
**Loyiha:** Totli Holva Business System (cft worktree)

---

## 1. Loyiha tuzilishi (qisqacha)

- **Backend:** FastAPI, SQLAlchemy, Python 3.12
- **Frontend:** Jinja2, Bootstrap 5, JavaScript
- **Asosiy fayllar:** `main.py` (route’lar), `app/models/database.py`, `app/templates/`, `app/utils/auth.py`
- **Ma’lumotlar bazasi:** SQLite (`totli_holva.db`), Alembic migratsiyalar
- **Modullar:** Tovarlar, Sotuvlar, Kirim, Ishlab chiqarish, Ombor, Kontragentlar, Agentlar, Yetkazish, Hisobotlar, Ma’lumotnomalar

---

## 2. Kechagi / so‘nggi o‘zgarishlar (tekshirilgan)

### Sotuvlar (Sales)
- **POST /sales/create** – `product_id` va `quantity` ro‘yxat sifatida: `request.form().getlist()` orqali qabul qilinadi; savat bir so‘rovda yuboriladi.
- **POST /sales/{id}/add-items** – Sotuv tahririda savat: bir nechta mahsulot qo‘shib “Barchasini buyurtmaga qo'shish” bilan bir so‘rovda qo‘shish.
- **Miqdor input** – `min="0"` va `step="0.01"`, `value="1"` (sales/edit va sales/new); brauzer “1” ni rad etmasligi uchun.

### Tovarlar import (Products import)
- **POST /products/import** – Fayl endi `File()` o‘rniga `await request.form()` dan olinadi; fayl bo‘lmasa 422 o‘rniga redirect `/products?error=import&detail=...`.
- **Forma** – “Fayl tanlash” va “Import qilish” tugmasi; fayl tanlangach “Import qilish” yoqiladi, shunda forma fayl bilan yuboriladi.
- **IndentationError** – `if not contents:` takrori olib tashlangan.

### Boshqa (oldingi commit’larda)
- Favicon, Yandex Maps apikey, OrderItem.product, tovar/sotuv o‘chirish, production revert redirect, shtrix kod, price-types JS, auth, test admin – hujjatlarda: `KAMCHILIKLAR_TEKSHIRUVI.md`, `KAMCHILIKLAR_QOLGAN.md`.

---

## 3. Tekshiruv (kamchiliklar)

- To‘liq ro‘yxat: **KAMCHILIKLAR_TEKSHIRUVI.md**
- Tekshirchi skript: **tekshirchi.py** (server, baza, production sahifasi)
- Asosiy funksiyalar va xavfsizlik bandlari tuzatilgan; CSRF va main.py modullarga bo‘lish ixtiyoriy qoldi.

---

## 4. Git va GitHub

- **Remote:** `origin` = https://github.com/elyaclassic/totli-holva-business-system.git
- So‘nggi o‘zgarishlar commit qilinadi va GitHub’ga push qilinadi.

---

*Fayl: LOYIHA_TAHLILI_VA_OZGARISHLAR.md*
