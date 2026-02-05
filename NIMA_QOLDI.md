# Yana nima qoldi — qisqacha ro'yxat

**Sana:** 2026-02-05

---

## ✅ Bajarilgan (so'nggi refaktor)

- **main.py** — Dashboard va /info bloklari routerlarga chiqarildi; main ~435 qator, keraksiz importlar olib tashlandi.
- **Dublikat /info** — main.py da yo'q, faqat `app/routes/info.py` da.
- **Routerlar:** auth, dashboard, home, reports, info — barchasi `include_router` orqali ulangan.

---

## 🔲 Tuzilma va kod (qolgan)

| # | Narsa | Qisqacha |
|---|--------|----------|
| 1 | **main.py da yana route'lar** | products, purchases, sales, warehouse, delivery, production, agents, map hali main.py da (yoki boshqa fayllarda `@app` bilan). Ularni ham alohida routerlarga ko'chirish mumkin. |
| 2 | **POST/delete da current_user** | Ba'zi info_*_delete va boshqa POST larda `require_auth` / `current_user` yo'q; audit va rol uchun qo'shish ma'qul. |
| 3 | **Qadoqlash uchun alohida menyu** | Agar kerak bo'lsa — `qadoqlash_menu` (faqat Qadoqlash, Ombor, Hisobot). |
| 4 | **page_title / current_user** | Barcha sahifalarda `page_title` va kerak bo'lsa `current_user` uzatilishini tekshirish. |
| 5 | **Eksport/import da auth** | `/info/*/export`, `/products/export` va sh.k. da `Depends(require_auth)` qo'yish (audit uchun). |

---

## 🔲 Funksional (hujjatlar bo'yicha)

| # | Muammo | Manba |
|---|--------|--------|
| 1 | **Ombor harakati** — `warehouse/movement.html` yo'q, 500 xato | TAHLIL_VA_TAKLIFLAR.md |
| 2 | **Uskunalar (Machine)** — CRUD/menyu main ga ulanmagan, dashboard da placeholder | TAHLIL_VA_TAKLIFLAR.md |
| 3 | **Kam qolgan tovar bildirishnomasi** — kirim/sotuv/production tasdiqda avtomatik chaqirilmaydi | TAHLIL_VA_TAKLIFLAR.md |
| 4 | **Hisobotlar eksport** — Savdo, qoldiq, qarzdorlik uchun Excel/PDF yo'q | TAHLIL_VA_TAKLIFLAR.md |
| 5 | **Bosh sahifa** — "Tug'ilgan kunlar", "Muddati o'tgan qarzlar" 0 (real hisoblash yo'q) | TAHLIL_VA_TAKLIFLAR.md |
| 6 | **Production + uskuna/operator** — machine_id, operator_id saqlanmaydi | TAHLIL_VA_TAKLIFLAR.md |
| 7 | **PWA** — lokatsiya intervali, offline sync to'liq emas | PWA_REJA.md |
| 8 | **Scheduler** — kunlik kam qoldiq / muddati o'tgan qarz tekshiruvi (bildirishnoma) | TAHLIL_VA_TAKLIFLAR.md |

---

## 🔲 Ixtiyoriy

- **CSRF** — Barcha forma POST larda token (ixtiyoriy).
- **RBAC** — Rol bo'yicha cheklovlarni kengaytirish.
- **Logging** — Login, foydalanuvchi o'zgarishlari, muhim harakatlar uchun log.
- **Production DB** — SQLite o'rniga PostgreSQL (production uchun).

---

## Qayerda batafsil

- **KAMCHILIKLAR_QOLGAN.md** — Tuzatilganlar va qolgan xavfsizlik/tuzilma.
- **LOYIHA_TAHLILI_2026_02.md** — Kamchiliklar va takliflar (9 band).
- **TAHLIL_VA_TAKLIFLAR.md** — Funksional bo'shliqlar va 8 ta taklif (raqam bilan tanlash mumkin).

Qaysi banddan boshlashni xohlasangiz, raqamini yozing (masalan: "2 va 4 ni qil").
