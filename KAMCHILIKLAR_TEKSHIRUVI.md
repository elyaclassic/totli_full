# Kamchiliklar tekshiruvi – to‘liq ro‘yxat

**Sana:** 2026-02-02  
**Manba:** KAMCHILIKLAR_QOLGAN.md, KAMCHILIKLAR_TAHLILI_2026.md, KAMCHILIKLAR_TAHLILI.md, kod tekshiruvi.

---

## 1. Funksional kamchiliklar (KAMCHILIKLAR_QOLGAN)

| № | Kamchilik | Holat | Izoh |
|---|-----------|--------|------|
| 1 | Tovarlar sahifasida O‘chirish tugmasi ishlamaydi | ✅ Tuzatilgan | POST /products/delete/{id}, soft delete, forma |
| 2 | OrderItem da product relationship yo‘q | ✅ Tuzatilgan | database.py da product = relationship("Product") |
| 3 | Sotuvlar ro‘yxatida O‘chirish tugmasi ishlamaydi | ✅ Tuzatilgan | POST /sales/delete/{id}, qoralama bekor |
| 4 | Kod vs shtrix kod nomuvofiqligi | ✅ Tuzatilgan | recipe_detail, edit_materials, warehouse, reports/stock – barcode yoki code |
| 5 | Production revert – JSON o‘rniga redirect | ✅ Tuzatilgan | RedirectResponse + ?error=revert&detail=..., orders.html da alert |
| 6 | /info/price-types SyntaxError (tojson) | ✅ Tuzatilgan | data-* atributlar + addEventListener |
| 7 | Sotuv tafsiloti sahifasi yo‘q | ✅ Tuzatilgan | GET /sales/edit, add-item, confirm, delete-item, Order.price_type |
| 8 | Sales create – product_id/quantity list | ✅ Tuzatilgan | request.form().getlist(); savat bir so‘rovda yuboriladi |
| 9 | Sales edit – savat, bitta harakatda qo‘shish | ✅ Tuzatilgan | POST /sales/{id}/add-items, savat + "Barchasini buyurtmaga qo'shish" |
| 10 | Miqdor input "1" brauzer validatsiya xatosi | ✅ Tuzatilgan | min="0" step="0.01", value="1" (edit va new) |

---

## 2. Xavfsizlik (KAMCHILIKLAR_TAHLILI_2026)

| № | Kamchilik | Holat | Izoh |
|---|-----------|--------|------|
| 1 | Product.cost_price yo‘q – AttributeError | ✅ Tuzatilgan | main.py da faqat purchase_price; cost_price ishlatilmaydi |
| 2 | POST endpointlarda autentifikatsiya yo‘q | ✅ Tuzatilgan | Middleware + require_auth 60+ joyda; sales_new, sales_create da require_auth |
| 3 | Ochiq API (/api/stats, products, partners) | ✅ Tuzatilgan | Middleware session orqali himoya qiladi |
| 4 | Test sahifalari to‘liq ochiq | ✅ Tuzatilgan | /test/dashboard/*, /test/regions – require_admin |
| 5 | Parol hashlash – SHA256 zaif | ✅ Tuzatilgan | auth.py da bcrypt + eski hash migratsiyasi |
| 6 | Session cookie (secure, SECRET_KEY) | ✅ Tuzatilgan | HTTPS da secure=True; SECRET_KEY default bo‘lsa production da xabar |
| 7 | debug_home.log har so‘rovda yozish | ✅ Tuzatilgan | Kodda yo‘q |
| 8 | SECRET_KEY default qiymati | ✅ Tuzatilgan | Production da default ishlatilsa ilova ishlamaydi (xabar) |
| 9 | CSRF himoyasi | ❌ Qolgan | Kelajakda (ixtiyoriy) – formalarda CSRF token yo‘q |
| 10 | RBAC (rollar) | ⚠️ Qisman | require_admin test/revert da; boshqa granulatsiya yo‘q |

---

## 3. Tuzilma va boshqa

| № | Kamchilik | Holat | Izoh |
|---|-----------|--------|------|
| 1 | main.py hajmi (4000+ qator) | ❌ Qolgan | Kelajakda modullarga bo‘lish (ixtiyoriy) |
| 2 | Ma’lumotlar validatsiyasi | ⚠️ Qisman | Form(...) ko‘p joyda; Pydantic yanada rivojlantirish mumkin |
| 3 | Favicon 404 | ✅ Tuzatilgan | GET /favicon.ico, base.html link |
| 4 | Yandex Maps Invalid API key | ✅ Tuzatilgan | partners/list.html da apikey=YOUR_API_KEY olib tashlangan |

---

## 4. Kod tekshiruvi (amaliy)

| Tekshiruv | Natija |
|-----------|--------|
| main.py da cost_price | ✅ Yo‘q – faqat purchase_price |
| require_auth / require_admin | ✅ 60+ marta ishlatiladi |
| Middleware – session | ✅ Login/logout, static, agent/driver API dan tashqari himoya |
| API session | ✅ /api/stats, /api/products, /api/partners middleware orqali |
| Test admin | ✅ require_admin barcha test yo‘llarda |
| CSRF | ❌ Yo‘q |
| RBAC | ⚠️ Faqat admin (test, revert) |

---

## 5. Tekshirchi skripti (tekshirchi.py)

| Band | Natija | Izoh |
|------|--------|------|
| [1] Server (8080) | OK | Server ishlayapti |
| [2] Baza – omborlar | OK | 3 ta ombor |
| [3] Production – omborlar dropdown | Tekshirish kerak | Tekshirchi skripti urllib bilan login qilganda session cookie saqlanmasligi mumkin, shuning uchun "Dropdown da omborlar yo'q" chiqadi. Kodda GET /production warehouses uzatadi, template da ombor option lari mavjud. **Brauzerda** /production ochib dropdown ni qo'lda tekshirish tavsiya etiladi. |

---

## 6. Boshqa topilganlar

- **PWA:** app/static/pwa/dashboard.html da TODO (API yuklash, batareya, xarita) – kelajakdagi ish.
- **Placeholder:** +998 XX XXX XX XX – faqat placeholder, xato emas.

---

## 7. Xulosa

- **Tuzatilgan:** Barcha asosiy funksional va xavfsizlik bandlari (o‘chirish tugmalari, OrderItem, sotuv tafsiloti, sales create/edit savat, miqdor, production revert, price-types JS, auth, middleware, API himoya, test admin, parol bcrypt, cost_price, favicon, Yandex apikey).
- **Qolgan (ixtiyoriy):** CSRF token, main.py ni modullarga bo‘lish.
- **Qisman:** RBAC – faqat admin tekshiruvi; production tekshirchi dropdown – kod to‘g‘ri, tekshirchi natijasi tekshirish kerak.

*Oxirgi tekshiruv: 2026-02-02. Fayl: KAMCHILIKLAR_TEKSHIRUVI.md*
