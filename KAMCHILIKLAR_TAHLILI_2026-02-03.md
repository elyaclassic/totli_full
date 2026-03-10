# TOTLI HOLVA – Loyiha kamchiliklari tahlili
**Sana:** 2026-02-03

---

## 1. Xavfsizlik

### 1.1 Parol hashlash zaif
**Fayl:** `app/utils/auth.py`

- Parol **SHA256** bilan hash qilinadi, **tuz (salt)** ishlatilmaydi.
- Bir xil parollar bir xil hash beradi; rainbow table hujumlari oson.
- **Tavsiya:** `passlib` (requirements.txt da bor) orqali **bcrypt** ishlating.

```python
# Hozirgi (zaif):
return hashlib.sha256(password.encode()).hexdigest()

# Tavsiya: passlib[bcrypt] dan foydalaning
```

### 1.2 SECRET_KEY default qiymati
**Fayl:** `app/utils/auth.py`

- `SECRET_KEY` uchun default: `"totli-holva-secret-key-2026-change-in-production"`.
- Production da environment o‘rnatilmasa, session tokenlar bashorat qilish mumkin.
- **Tavsiya:** Production da `SECRET_KEY` ni faqat environment orqali o‘rnating; default bo‘lmasin yoki ishga tushganda tekshiring.

### 1.3 Login xato xabari – ma’lumot sizdirish
**Fayl:** `main.py` (~128-qator)

- Xato paytida foydalanuvchiga `str(e)` ko‘rsatiladi.
- Ichki xatoliklar (DB, fayl yo‘li va h.k.) tashqariga chiqadi.
- **Tavsiya:** Foydalanuvchiga faqat umumiy xabar: *"Tizimda xatolik. Keyinroq urinib ko‘ring."*; to‘liq xato faqat logga yozilsin.

### 1.4 Himoyasiz endpointlar
**Muammo:** Ko‘plab marshrutlar **autentifikatsiya talab qilmaydi**.

Himoyasiz (yoki faqat GET himoyalangan) endpointlar misollari:

| Marshrut | Tavsif |
|----------|--------|
| `POST /info/warehouses/add`, `edit`, `delete` | Auth yo‘q |
| `GET/POST /info/warehouses/export`, `import`, `template` | Auth yo‘q |
| `POST /info/units/add`, `edit`, `delete` va export/import | Auth yo‘q |
| `POST /info/categories/*`, `info/cash/*`, `info/departments/*`, `info/directions/*` | Auth yo‘q |
| `GET /products/export`, `template`, `{id}` | Auth yo‘q |
| `POST /products/import`, `add`, `upload-image` | Auth yo‘q |
| `GET/POST /purchases/*`, `sales/*`, `partners/*` | Ko‘pida auth yo‘q |
| `GET /dashboard/executive`, `sales`, `agent`, `production`, `warehouse`, `delivery` | Auth yo‘q |
| `GET /dashboard/executive/live`, `warehouse/live`, `delivery/live` | Auth yo‘q |
| `GET /api/stats`, `/api/products`, `/api/partners` | Auth yo‘q |

**Tavsiya:** Barcha ma’lumot o‘zgartiruvchi va maxfiy ma’lumot ko‘rsatuvchi endpointlarda `current_user: User = Depends(require_auth)` qo‘ying va kerak bo‘lsa role tekshiring.

### 1.5 Cookie: secure=False
**Fayl:** `main.py` (~115)

- `secure=False` – cookie HTTPS orqali yuborilmaydi.
- Development uchun ma’qul; production da HTTPS ishlatilsa `secure=True` qilish kerak (config orqali).

---

## 2. Mantiqiy xatolar

### 2.1 Agent/Driver API: token da "role" yo‘q
**Fayl:** `main.py` – `/api/agent/location`, `/api/driver/location`

- Token `create_session_token(user.id, user.username)` bilan yaratiladi – token ichida **user_type = username** saqlanadi, **role** saqlanmaydi.
- Kodda: `user_data.get("role") != "agent"` / `!= "driver"` tekshiriladi; token da `"role"` yo‘q, shuning uchun doim `Invalid token` qaytadi.
- **Tavsiya:** Token ga role qo‘shing yoki token dan `user_id` olib, DB dan `User` ni oling va `user.role` ni tekshiring.

### 2.2 Excel import – xato va validatsiya
**Fayl:** `main.py` – `import_products`, `import_warehouses`, va boshqa import endpointlar

- `row[1:8]` da `None` yoki yetarli ustun bo‘lmasa – `category_name.lower()` kabi joylarda **AttributeError**.
- Fayl formati (xlsx) va maksimal hajmi tekshirilmaydi – noto‘g‘ri yoki yirik fayl serverga yuklansa xatolik yoki overload bo‘lishi mumkin.
- **Tavsiya:** Qatorni validatsiya qiling (None, bo‘sh qator), try/except va aniq xabar; fayl hajmi va kengaytmani cheklang.

---

## 3. Kod sifati va barqarorlik

### 3.1 Windows konsoli va emoji
**Fayllar:** `main.py`, `app/models/database.py`

- `print("✅ ...")`, `print("❌ ...")` va startup dagi emoji Windows (cp1251) da **UnicodeEncodeError** berishi mumkin.
- **Tavsiya:** Logging ishlating; agar print qolsа, faqat ASCII matn (emoji ishlatmaslik).

### 3.2 Bosh sahifa – har so‘rovda faylga yozish
**Fayl:** `main.py` – `home()` (~1487–1548)

- Har bir `/` so‘rovida `debug_home.log` ga yoziladi.
- Production da diskni to‘ldirishi va I/O ortiqcha yuklashi mumkin.
- **Tavsiya:** Debug logni faqat development rejimida yozing yoki logging moduliga o‘tkazing va darajani sozlang.

### 3.3 API xato javobi – ichki xato matni
**Fayl:** `main.py` – `/api/agent/location`, `/api/driver/location` va boshqa API

- `return {"success": False, "error": str(e)}` – ichki exception matni tashqariga chiqadi.
- **Tavsiya:** Client uchun umumiy xabar; to‘liq `str(e)` faqat logda saqlansin.

### 3.4 require_auth – 401 emas, None
**Fayl:** `main.py` – `require_auth`

- Login qilmagan foydalanuvchi uchun **None** qaytadi; 401 qaytarilmaydi.
- Har bir endpoint o‘zida `if not current_user: return RedirectResponse("/login")` qilishi kerak; bir joyda unutsa, himoya buziladi.
- **Tavsiya:** `require_auth` ichida agar user bo‘lmasa **HTTPException(401)** yoki **RedirectResponse("/login")** qaytaring, yoki alohida `require_auth_strict` dependency yarating.

---

## 4. Test va maxsus marshrutlar

### 4.1 Test dashboardlar – auth yo‘q
**Fayl:** `main.py`

- `/test/dashboard/executive`, `/test/dashboard/sales`, `/test/dashboard/agent`, `/test/dashboard/production`, `/test/dashboard/warehouse`, `/test/dashboard/delivery` – **autentifikatsiyasiz**.
- Production da ochiq qolsa, ma’lumotlar ko‘rinadi.
- **Tavsiya:** Production da bu marshrutlarni o‘chiring yoki faqat DEBUG/development rejimida yoqilsin.

---

## 5. Qisqacha tavsiyalar

| Tartib | Kamchilik | Qisqa chora |
|--------|-----------|-------------|
| 1 | Parol SHA256, tuz yo‘q | bcrypt (passlib) ishlating |
| 2 | SECRET_KEY default | Prod da env dan oling, default qo‘ymang |
| 3 | Login/API xato matni | Foydalanuvchiga umumiy xabar, to‘liq xato faqat logda |
| 4 | Ko‘p endpointda auth yo‘q | CRUD va dashboard larda require_auth qo‘shing |
| 5 | Agent/Driver API role | Token da role yoki DB dan user.role tekshiring |
| 6 | Excel import | None/validatsiya va try/except, fayl hajmi cheklovi |
| 7 | print + emoji | Logging, ASCII matn (yoki emojisiz) |
| 8 | debug_home.log har so‘rovda | Faqat dev yoki logging darajasi orqali |
| 9 | Test dashboardlar | Prod da o‘chiring yoki faqat dev rejimida |
| 10 | require_auth 401 | None o‘rniga 401 yoki redirect markazlashtiring |

Agar xohlasangiz, keyingi qadamda xavfsizlik (auth + parol) yoki import validatsiyasidan boshlab aniq kod o‘zgarishlarini taklif qilish mumkin.
