# TOTLI HOLVA - Kamchiliklarni Tuzatish Rejasi

**Sana:** 2026-01-27  
**Maqsad:** Kamchiliklar tahlilida aniqlangan muammolarni tuzatish

---

## 📋 TUZATISH KETMA-KETLIGI

### ✅ BOSQICH 1: Sidebar Menyusini Tuzatish (BAJARILMOQDA)
**Muammo:** Sidebar menyusida "Ma'lumotlar" bo'limida `/products`, `/partners`, `/employees` ko'rsatilgan, lekin ular aslida alohida modullar.

**Yechim:**
1. `base.html` da sidebar menyusini qayta tuzish
2. "Ma'lumotlar" bo'limidan Tovarlar, Kontragentlar, Xodimlarni chiqarish
3. Ularni alohida bo'limlarga joylashtirish

**Natija:** Navigatsiya mantiqiy va tushunarli bo'ladi.

---

### ⏳ BOSQICH 2: Autentifikatsiya Tizimini Qo'shish
**Muammo:** Login/logout funksiyalari yo'q.

**Qadamlar:**
1. `/login` sahifasini yaratish
2. `/logout` endpointini qo'shish
3. Session boshqaruvi (FastAPI SessionMiddleware)
4. Password hashing (bcrypt)
5. Login required decorator yaratish
6. Barcha sahifalarni himoyalash

**Fayl o'zgarishlari:**
- `main.py` - autentifikatsiya endpointlari
- `app/templates/login.html` - yangi fayl
- `app/templates/base.html` - logout tugmasi
- `requirements.txt` - `passlib[bcrypt]` qo'shish

---

### ⏳ BOSQICH 3: Database Munosabatlarini To'ldirish
**Muammo:** `Department` va `Direction` modellari boshqa modellar bilan bog'lanmagan.

**Qadamlar:**
1. `Employee` modeliga `department_id` qo'shish
2. `Product` modeliga `direction_id` qo'shish
3. `Production` modeliga `department_id` va `direction_id` qo'shish
4. Alembic migration yaratish
5. Frontend sahifalarini yangilash (dropdown'lar qo'shish)

**Fayl o'zgarishlari:**
- `app/models/database.py` - modellarni yangilash
- `alembic/versions/` - yangi migration
- `app/templates/employees/list.html` - bo'lim tanlash
- `app/templates/products/list.html` - yo'nalish tanlash

---

### ⏳ BOSQICH 4: Xatoliklarni Boshqarishni Yaxshilash
**Muammo:** Frontend va backend o'rtasida xatoliklarni boshqarish zaif.

**Qadamlar:**
1. Barcha CRUD endpointlarini JSON response qaytaradigan qilish
2. Frontend da AJAX so'rovlar (fetch API)
3. Global error handler yaratish
4. Toast notification sistemasini barcha sahifalarga qo'shish

**Fayl o'zgarishlari:**
- `main.py` - JSON response'lar
- `app/static/js/common.js` - yangi fayl (umumiy funksiyalar)
- Barcha HTML sahifalar - AJAX bilan yangilash

---

### ⏳ BOSQICH 5: Qidiruv va Filtrlash
**Muammo:** Ro'yxat sahifalarida qidiruv yo'q.

**Qadamlar:**
1. Backend da qidiruv parametrlarini qo'shish
2. Frontend da qidiruv input va filtrlash dropdown'lari
3. Pagination qo'shish (10, 25, 50, 100 ta)
4. Real-time qidiruv (debounce bilan)

**Fayl o'zgarishlari:**
- `main.py` - qidiruv parametrlari
- Barcha list.html sahifalar - qidiruv UI

---

### ⏳ BOSQICH 6: Ma'lumotlar Validatsiyasi
**Muammo:** Validatsiya yetarli emas.

**Qadamlar:**
1. Pydantic modellarini yaratish
2. Backend validatsiyasini qo'shish
3. Frontend validatsiyasini qo'shish
4. Database constraint'lar

**Fayl o'zgarishlari:**
- `app/models/schemas.py` - yangi fayl (Pydantic schemas)
- `main.py` - Pydantic modellardan foydalanish
- HTML sahifalar - JavaScript validatsiyasi

---

### ⏳ BOSQICH 7: Export/Import Kengaytirish
**Muammo:** Faqat mahsulotlar uchun mavjud.

**Qadamlar:**
1. Kontragentlar export/import
2. Xodimlar export/import
3. Kategoriyalar export/import
4. O'lchov birliklari export/import

**Fayl o'zgarishlari:**
- `main.py` - yangi export/import endpointlari
- HTML sahifalar - export/import tugmalari

---

### ⏳ BOSQICH 8: Logging Tizimi
**Muammo:** Log yozish yo'q.

**Qadamlar:**
1. Python logging konfiguratsiyasi
2. Audit log modeli (kim, qachon, nima qildi)
3. Error logging
4. Log viewer sahifasi (admin uchun)

**Fayl o'zgarishlari:**
- `app/utils/logging.py` - yangi fayl
- `app/models/database.py` - AuditLog modeli
- `main.py` - logging middleware

---

### ⏳ BOSQICH 9: Xavfsizlik Yaxshilash
**Muammo:** CSRF, XSS himoyasi yo'q.

**Qadamlar:**
1. CSRF token qo'shish
2. XSS himoyasi (Jinja2 auto-escape faol)
3. Rate limiting
4. HTTPS majburiy qilish (production uchun)

**Fayl o'zgarishlari:**
- `main.py` - CSRF middleware
- `requirements.txt` - `slowapi` (rate limiting)

---

### ⏳ BOSQICH 10: Backup va Recovery
**Muammo:** Backup mexanizmi yo'q.

**Qadamlar:**
1. Avtomatik backup skripti
2. Backup schedule (kunlik, haftalik)
3. Restore funksiyasi
4. Backup viewer sahifasi

**Fayl o'zgarishlari:**
- `backup_script.py` - yangi fayl
- `restore_script.py` - yangi fayl
- Windows Task Scheduler uchun `.bat` fayl

---

## 📊 PROGRESS TRACKER

| Bosqich | Status | Vaqt (taxminiy) |
|---------|--------|-----------------|
| 1. Sidebar tuzatish | 🟡 Bajarilmoqda | 15 daqiqa |
| 2. Autentifikatsiya | ⏳ Kutilmoqda | 2 soat |
| 3. Database munosabatlar | ⏳ Kutilmoqda | 1.5 soat |
| 4. Error handling | ⏳ Kutilmoqda | 2 soat |
| 5. Qidiruv/filtrlash | ⏳ Kutilmoqda | 3 soat |
| 6. Validatsiya | ⏳ Kutilmoqda | 2 soat |
| 7. Export/Import | ⏳ Kutilmoqda | 2 soat |
| 8. Logging | ⏳ Kutilmoqda | 1.5 soat |
| 9. Xavfsizlik | ⏳ Kutilmoqda | 2 soat |
| 10. Backup | ⏳ Kutilmoqda | 1 soat |

**JAMI:** ~17 soat

---

## 🎯 USTUVOR TARTIB

1. **Sidebar tuzatish** (15 daqiqa) - Hozir
2. **Autentifikatsiya** (2 soat) - Bugun
3. **Database munosabatlar** (1.5 soat) - Bugun
4. **Error handling** (2 soat) - Ertaga
5. **Qidiruv/filtrlash** (3 soat) - Ertaga
6. Qolganlar - keyingi kunlar

---

## 📝 ESLATMALAR

- Har bir bosqichdan keyin test qilish
- Git commit qilish (agar git ishlatilsa)
- Backup olish (database)
- Hujjatlarni yangilash
