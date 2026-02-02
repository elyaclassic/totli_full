# Qolgan kamchiliklar – qisqacha ro‘yxat

Tahlil qilingan joylar va hujjatlar asosida quyidagi nuqsonlar aniqlandi.

---

## Tuzatilganlar (2026-02-02)

- **1. Tovarlar O‘chirish** – `POST /products/delete/{product_id}` (soft delete: `is_active=False`) qo‘shildi; ro‘yxatda forma + tasdiq. Tovarlar ro‘yxati faqat `is_active == True` ko‘rsatadi.
- **2. OrderItem** – `product = relationship("Product")` qo‘shildi; sotuv tafsilotida mahsulot nomi ishlaydi.
- **3. Sotuvlar O‘chirish** – `POST /sales/delete/{order_id}` qo‘shildi (faqat qoralama bekor qilinadi); ro‘yxatda qoralama uchun forma. Xato xabari sahifada ko‘rsatiladi.
- **4. Kod / shtrix kod** – Retsept tafsiloti, ishlab chiqarish materiallari, ombor ro‘yxati, hisobot/stock sahifalarida endi **shtrix kod bo‘lsa shtrix kod, yo‘q bo‘lsa kod** qoidasi qo‘llanadi.
- **5. Production revert** – Xato paytida `RedirectResponse` bilan `/production/orders?error=revert&detail=...`; sahifada alert ko‘rsatiladi.
- **6. price-types SyntaxError** – `onclick` ichidagi `tojson` o‘rniga tugmalarda `data-id`, `data-name`, `data-code` va addEventListener orqali xavfsiz o‘qish.

**Tuzatilganlar (2026-02-02, 2-qism – hamma kamchiliklarni bartaraf etish):**

- **Sotuv tafsiloti** – `GET /sales/edit/{order_id}` route, `sales/edit.html` shabloni, `POST /sales/{order_id}/add-item`, `POST /sales/{order_id}/confirm`, `POST /sales/{order_id}/delete-item/{item_id}` qo‘shildi. Sotuvda mahsulotlar, jami, tasdiqlash/bekor qilish ishlaydi. `Order.price_type` relationship qo‘shildi.
- **Sales auth** – `sales_new` va `sales_create` da `require_auth` qo‘yildi.
- **Test sahifalari** – Barcha `/test/dashboard/*` va `/test/regions` endi `require_admin` bilan faqat admin uchun ochiq.
- **POST/API himoya** – Middleware barcha yo‘llarni (login/logout/static va agent/driver API dan tashqari) session orqali himoya qiladi; API va POST allaqachon himoyalangan.
- **Parol** – `app/utils/auth.py` da bcrypt va eski hash migratsiyasi mavjud.
- **cost_price / debug_home.log** – Kodda `purchase_price` ishlatiladi, `debug_home.log` yo‘q.

**Kelajakda (ixtiyoriy):** CSRF token barcha formalarga, main.py ni modullarga bo‘lish.

---

## 1. ~~Tovarlar sahifasida **O‘chirish** tugmasi ishlamaydi~~ ✅ Tuzatildi

**Joy:** `app/templates/products/list.html` – qizil o‘chirish tugmasi.

**Muammo:** Tugmada `onclick`, `form` yoki `action` yo‘q. Endpoint ham yo‘q: `POST /products/delete/{product_id}` mavjud emas.

**Kerak:** Tovar o‘chirish uchun POST route qo‘shish (masalan soft delete: `is_active = False`) va shablonda forma/JS bilan ushbu endpointga so‘rov yuborish.

---

## 2. ~~**OrderItem** da `product` relationship yo‘q~~ ✅ Tuzatildi

**Joy:** `app/models/database.py` – `OrderItem` (buyurtma qatorlari, sotuvlar).

**Muammo:** `OrderItem` da `product_id` bor, lekin `product = relationship("Product")` yo‘q. Agar sotuv tafsilot sahifasida `item.product.name` ishlatilsa, xato yoki bo‘sh qiymat chiqadi.

**Kerak:** `OrderItem` ga `product = relationship("Product")` qo‘shish (xuddi `PurchaseItem` da qilgandek).

---

## 3. ~~Sotuvlar ro‘yxatida **O‘chirish** tugmasi ishlamaydi~~ ✅ Tuzatildi

**Joy:** `app/templates/sales/list.html` – har bir sotuv qatoridagi o‘chirish tugmasi.

**Muammo:** Tugma faqat ko‘rinadi, hech qanday `form`/`action` yo‘q. `POST /sales/delete/{id}` yoki shunga o‘xshash endpoint bor-yo‘qligi tekshirilishi kerak.

**Kerak:** Sotuvni bekor qilish/o‘chirish logikasi va endpoint bo‘lsa, shablonda forma bilan ulash; bo‘lmasa, endpoint + shablon qo‘shish.

---

## 4. ~~Boshqa sahifalarda **kod** vs **shtrix kod** nomuvofiqligi~~ ✅ Tuzatildi

**Joylar:**
- `app/templates/production/recipe_detail.html` – `item.product.code`
- `app/templates/production/edit_materials.html` – `pi.product.code`
- `app/templates/warehouse/list.html` – `stock.product.code`
- `app/templates/reports/stock.html` – `stock.product.code`

**Muammo:** Narxni o‘rnatish sahifasida mahsulot ostida shtrix kod ko‘rsatiladi; boshqa joylarda hali **kod** (masalan P49) ko‘rsatiladi. Bir xil qoida keltirish kerak.

**Kerak:** Hamma joyda shtrix kod ko‘rsatish yoki “shtrix kod bo‘lsa shtrix kod, yo‘q bo‘lsa kod” qoidasini qo‘llash.

---

## 5. ~~**Production revert** – forma POST da JSON o‘rniga redirect kerak~~ ✅ Tuzatildi

**Joy:** `main.py` – `POST /production/{prod_id}/revert`.

**Muammo:** Purchases revert da qilgandek: xato paytida `HTTPException(400, ...)` qaytariladi, brauzer JSON ko‘rsatadi. Forma orqali bosilganda foydalanuvchi sahifada xabar ko‘rishi ma’qul.

**Kerak:** Xato paytida `db.rollback()` va `RedirectResponse` bilan tegishli edit sahifasiga `?error=revert&detail=...` qo‘shib yo‘naltirish; sahifada alert ko‘rsatish.

---

## 6. ~~**/info/price-types** sahifasida brauzerda SyntaxError~~ ✅ Tuzatildi

**Belgi:** Brauzer konsolida `Uncaught SyntaxError: Unexpected end of input (at price-types:628:142)` (yoki 633:142).

**Ehtimol sabab:** Sahifa HTML ida qaysidir `<script>` da yopilmagan qavs/string yoki `tojson` filter natijasida chiqayotgan maxsus belgilar. `/info/price-types` va `info/price_types.html` + `base.html` birlashmasida 628-qator atrofidagi script tekshirilishi kerak.

**Kerak:** Shu qator atrofidagi JS ni tekshirish, string/quote va `tojson` chiqishini xavfsizlashtirish.

---

## 7. Hujjatlar va avvalgi tahlillardan qolgan muhim bandlar

**KAMCHILIKLAR_TAHLILI_2026.md** da keltirilgan (qisqacha):

- **POST endpointlarda auth** – Ba’zi POST larda `require_auth` / `current_user` ishlatilmaydi; barcha ma’lumot o‘zgartiruvchi route larda auth tekshiruvi qo‘yish.
- **Ochiq API** – `/api/stats`, `/api/products`, `/api/partners` va h.k. session/token bilan himoyalanishi kerak.
- **Test sahifalari** – `/test/dashboard/...`, `/test/regions` production da o‘chirish yoki faqat admin/dev rejimida ochish.
- **Parol hashlash** – bcrypt (yoki argon2) ishlatish va mavjud parollarni migratsiya.
- **CSRF** – Forma POST larda CSRF token qo‘shish.
- **RBAC** – Rollar bo‘yicha cheklov (masalan faqat admin ba’zi o‘chirish/tahrirlash qilsin).
- **main.py hajmi** – Route larni modullarga (router) bo‘lish.

Batafsil: `KAMCHILIKLAR_TAHLILI_2026.md` va `KAMCHILIKLAR_TAHLILI.md`.

---

## Qolgan ishlar (endi nimalar qoldi)

### Funksional

- ~~**Sotuv tafsiloti sahifasi yo‘q**~~ ✅ GET /sales/edit, sales/edit.html, add-item, confirm, delete-item qo‘shildi.

### Xavfsizlik va tuzilma (KAMCHILIKLAR_TAHLILI_2026)

- **POST larda auth** – Middleware himoya qiladi; sales_new, sales_create da require_auth qo‘yildi.
- **API** – Middleware /api/* ni session orqali himoya qiladi.
- ~~**Test sahifalari**~~ ✅ Barcha test yo‘llar endi require_admin (faqat admin).
- **Parol** – auth.py da bcrypt va migratsiya mavjud.
- **CSRF** – Kelajakda (ixtiyoriy).
- **RBAC** – require_admin test va revert larda qo‘llanadi.
- **main.py hajmi** – Kelajakda (ixtiyoriy).

### Boshqa

- **cost_price** – Kodda purchase_price ishlatiladi. ~~**Debug log**~~ – Kodda yo‘q.

Batafsil: `KAMCHILIKLAR_TAHLILI_2026.md`, `KAMCHILIKLAR_TAHLILI.md`.

---

*Fayl yaratilgan: 2026-02-02. Oxirgi yangilanish: 2026-02-02 – barcha asosiy kamchiliklar bartaraf etildi (sotuv tafsiloti, auth, test admin).*
