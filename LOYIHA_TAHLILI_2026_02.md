# Loyiha tahlili – kamchiliklar va takliflar (2026-02)

Tizim: **TOTLI HOLVA** biznes boshqaruv tizimi (FastAPI, SQLite, Jinja2).

---

## Yaxshi ishlangan qismlar

- **Autentifikatsiya:** Login/logout, session (cookie), bcrypt parol.
- **Rol asosida menyu:** admin/manager/user (to‘liq), agent/driver (qisqa), production (ishlab chiqarish).
- **Login dan keyin yo‘naltirish:** agent → /dashboard/agent, production → /production.
- **Foydalanuvchilar:** Yangi/tahrirlash/parol/o‘chirish, rollar (admin, manager, user, production, qadoqlash, agent, driver), faqat admin uchun parolni ko‘rsatish.
- **Ishlab chiqarish bosqichlari:** ProductionStage, 4 bosqich, /production/orders da ko‘rinadi.
- **Modallar:** Foydalanuvchilar modallari body darajasida, z-index va JS orqali bosish ishlaydi.
- **Xato boshqaruvi:** global_safe_middleware, server_error.log, HTML so‘rovlarda /login?error=please_retry.
- **Test sahifalari:** /test/dashboard/* faqat require_admin.

---

## Qolgan kamchiliklar (tuzatish kerak)

### 1. **main.py juda katta (5000+ qator, 156 ta route)**

- Asosiy routelar (auth, home, reports, info) routerlarga chiqarilgan, lekin ko‘p route hali **main.py** da.
- **Taklif:** Dashboard, products, purchases, sales, warehouse, delivery, production, agents, map va boshqa bo‘limlarni alohida routerlarga bo‘lib, main.py da faqat `include_router` va middleware qoldirish.

### 2. **Dashboard routelarida auth bir xil emas**

- `/dashboard/executive`, `/dashboard/sales`, `/dashboard/agent`, `/dashboard/production`, `/dashboard/warehouse`, `/dashboard/delivery` da **Depends(require_auth)** yo‘q.
- Session cookie orqali qo‘lda tekshiruv bor (session_token, get_user_from_token). Bu ishlaydi, lekin **require_auth** ishlatilsa kod soddalashadi va xavfsizlik bir xil bo‘ladi.
- **Taklif:** Barcha dashboard handlerlarga `current_user: User = Depends(require_auth)` qo‘shib, ichidagi qo‘lda session tekshiruvini olib tashlash.

### 3. **Ba‘zi POST/delete handlerlarda current_user yo‘q**

- Masalan: `info_units_delete`, `info_categories_delete`, `info_cash_delete`, `info_departments_delete`, `info_directions_delete` va boshqalarda faqat `Depends(get_db)` bor.
- Middleware POST ni himoya qiladi, lekin route darajasida **kim** o‘chiryapti (audit) yozib olmaydi va kelajakda rol cheklovi qo‘shish qiyin.
- **Taklif:** Ma’lumot o‘zgartiruvchi va o‘chiruvchi barcha POST larda `current_user: User = Depends(require_auth)` (yoki admin kerak bo‘lsa require_admin) qo‘yish.

### 4. **Qadoqlash roli uchun alohida menyu yo‘q**

- **base.html** da `production_menu` va `agent_menu` bor; **qadoqlash** roli hozir **else** blokda (to‘liq menyu) ko‘rinadi.
- Agar qadoqlash xodimi uchun faqat ma’lum bo‘limlar (masalan Qadoqlash, Ombor, Hisobot) kerak bo‘lsa, **qadoqlash_menu** qo‘shib, sidebar da qisqa menyu ko‘rsatish mumkin.

### 5. **Sahifalarda page_title / current_user izi**

- **base.html** `<title>{{ page_title }} - TOTLI HOLVA</title>` va `current_user` ishlatadi.
- Agar bitta sahifa **page_title** yoki **current_user** uzatmasa, sarlavha bo‘sh yoki sidebar noto‘g‘ri rol ko‘rsatishi mumkin.
- **Taklif:** Barcha `TemplateResponse` larni tekshirib, `page_title` va kerak bo‘lsa `current_user` har doim uzatilishini ta’minlash (yoki globals/context processor orqali).

### 6. **Eski /info route lari va main.py dublikati**

- **app/routes/info.py** da prefix `/info` bilan routelar bor (masalan /info/warehouses).
- **main.py** da ham `/info/units`, `/info/categories`, `/info/price-types` va boshqalar aniqlangan (ba’zilari comment da).
- Bir xil path ikki joyda bo‘lsa, ro‘yxatga olish tartibiga qarab bitta ishlaydi; boshqasi ishlamasligi mumkin. **Tekshirish kerak:** qaysi /info/* routelar faqat main.py da, qaysilari faqat info routerda, dublikat yo‘qligiga ishonch hosil qilish.

### 7. **Parol maydonlari – autocomplete**

- Brauzer DOM ogohlantirishi: password inputlarda **autocomplete** tavsiya etiladi.
- **Yangi foydalanuvchi** va **Parolni o‘zgartirish** modallarida `autocomplete="new-password"` qo‘shilgan.
- **login.html** dagi parol maydonida ham `autocomplete="current-password"` qo‘yish ma’qul (konsol ogohlantirishini kamaytiradi).

### 8. **404 / 500 sahifalari**

- 404 (topilmadi) va 500 (server xatosi) uchun maxsus HTML sahifa (masalan `404.html`, `500.html`) bo‘lmasa, brauzer oddiy xabar ko‘rsatadi.
- **Taklif:** Exception handler larda HTML response qaytarish yoki tizim uslubidagi oddiy xato sahifasi (title, matn, orqaga link).

### 9. **Eksport/import endpointlari**

- `/info/units/export`, `/info/categories/export`, `/products/export` va shu kabi yo‘llarda odatda `Depends(get_db)` bor, **require_auth** yo‘q.
- Middleware barcha yo‘llarni himoya qilayotgan bo‘lsa, amalda himoya bor. Baribir **audit** va **kelajakdagi ruxsat** uchun export/import da ham `current_user: User = Depends(require_auth)` qo‘yish ma’qul.

---

## Ixtiyoriy yaxshilashlar

- **CSRF:** Barcha forma POST larda CSRF token (allaqachon middleware/cookie mavjud; formalarda input tekshiruvi).
- **RBAC:** Ba’zi harakatlar faqat admin (masalan foydalanuvchi o‘chirish, tizim sozlamalari) – bu qismlar require_admin bilan qoplangan; boshqa modullarda ham rol tekshiruvi kengaytirilishi mumkin.
- **Logging:** Muhim harakatlar (login, foydalanuvchi qo‘shish/o‘zgartirish, ishlab chiqarish bosqich) uchun log (kim, qachon, nima) yozish.
- **Baza:** Production da SQLite o‘rniga PostgreSQL yoki boshqa server DB ni qo‘llash; migratsiyalar hozircha Alembic orqali tartibli.

---

## Qisqacha ro‘yxat (tuzatish tartibi)

| # | Kamchilik | Qiyinlik | Holat |
|---|-----------|----------|--------|
| 1 | main.py juda katta | O‘rta | **Qoldi** – routelarni routerlarga bo‘lish |
| 2 | Dashboard da require_auth yo‘q | Oson | **Bajarildi** |
| 3 | Ba‘zi POST/delete da current_user yo‘q | Oson | **Bajarildi** |
| 4 | Qadoqlash uchun alohida menyu | Oson | **Bajarildi** (qadoqlash_menu + login yo'naltirish) |
| 5 | page_title / current_user izi | Oson | **Bajarildi** (product_detail, purchase_new, finance va b.) |
| 6 | /info route dublikati | Oson | **Qoldi** – main vs info router tekshirish |
| 7 | Login parol autocomplete | Oson | **Bajarildi** |
| 8 | 404/500 HTML sahifa | Oson | **Bajarildi** (404; 500 matni tayyor) |
| 9 | Export/import da auth | Oson | **Bajarildi** (barcha export/import/template) |

*Oxirgi yangilanish: 2026-02 – 4, 5, 9 bajarildi. Qoldi: 1 (main.py refaktor), 6 (info dublikati).*
