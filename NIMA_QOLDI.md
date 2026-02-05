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
| ~~2~~ | ~~POST/delete da current_user~~ | ✅ Info barcha POST (add/edit) larda `require_auth` qo'yildi. |
| ~~3~~ | ~~Qadoqlash uchun alohida menyu~~ | ✅ base.html da `qadoqlash_menu` mavjud. |
| 4 | **page_title / current_user** | Barcha sahifalarda `page_title` va kerak bo'lsa `current_user` uzatilishini tekshirish. |
| ~~5~~ | ~~Eksport/import da auth~~ | ✅ Eksport/import va products add/edit da `require_auth` bor. |

---

## 🔲 Funksional (hujjatlar bo'yicha)

| # | Muammo | Manba |
|---|--------|--------|
| ~~1~~ | ~~Ombor harakati~~ | ✅ movement.html mavjud; route xavfsiz (bo'sh ro'yxatlar), template None-safe. |
| ~~2~~ | ~~Uskunalar (Machine)~~ | ✅ /info/machines CRUD va menyuda (base.html) mavjud. |
| ~~3~~ | ~~Kam qolgan tovar bildirishnomasi~~ | ✅ Purchase confirm, sales confirm, production complete da check_low_stock_and_notify chaqiriladi. |
| ~~4~~ | ~~Hisobotlar eksport~~ | ✅ Savdo, qoldiq, qarzdorlik uchun /reports/*/export Excel mavjud. |
| ~~5~~ | ~~Bosh sahifa~~ | ✅ Tug'ilgan kunlar va muddati o'tgan qarzlar home.py da real hisoblanadi. |
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
