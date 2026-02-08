# Loyiha holati va mobil versiya rejasi

## ✅ Bajarilgan ishlar (ombor o'tkazish)

- **Tasdiqlashni bekor qilish** — tasdiqlangan hujjat uchun "Tasdiqlashni bekor qilish" tugmasi (faqat admin).
- **O'chirish qoidasi** — tasdiqlangan hujjatni to'g'ridan-to'g'ri o'chirish mumkin emas; avval tasdiq bekor qilinadi, keyin qoralama o'chiriladi.
- **Saqlashdan keyin** — saqlagach ro'yxat sahifasiga yo'naltirish va "Hujjat saqlandi" xabari.
- **Bildirishnoma** — "Hujjat o'chirildi" / "Hujjat saqlandi" xabarlari URL dan parametr olib tashlash orqali yangilashda qayta chiqmasligi ta'minlangan.

---

## 📱 Mobil versiya va APK rejasi

### Hozirgi holat

| Qism | Holat |
|------|--------|
| **Asosiy sayt (FastAPI)** | Ishlamoqda; ba'zi sahifalar mobilda sidebar yashirinadi (`mobile.css`). |
| **PWA (Agent)** | `app/static/pwa/` — login, dashboard, manifest, service worker mavjud; to'liq API va GPS integratsiyasi rejada. |
| **Android ilova** | WebView ilova mavjud (`android_app/`); hozir **ngrok** URL ga ulangan (`/static/pwa/login.html`). |

### Bosqich 1: Loyihaning mobil versiyasini yaxshilash

1. **Asosiy saytni mobilga moslashtirish**
   - Barcha muhim sahifalarda viewport va responsive tekshiruvi.
   - Mobil menyu (hamburger) — sidebar o'rniga yuqorida yoki ochiladigan menyu.
   - Jadvallar va formalar kichik ekranda qulay (scroll, kenglik, tugmalar).
   - Login, ro'yxatlar, ombor o'tkazish, sotuv, kirim va h.k. mobil qurilmalarda sinovdan o'tkazish.

2. **PWA ni asosiy tizimga ulash (ixtiyoriy)**
   - Agent/driver uchun PWA: login → dashboard → buyurtmalar/lokatsiya.
   - PWA ning API manzilini sozlanadigan qilish (ngrok o'rniga server URL).

3. **Yagona kirish nuqtasi**
   - Mobil qurilma aniqlansa yoki PWA dan kirilsa: bir xil login, keyin rol bo‘yicha (admin/agent/driver) mos sahifaga yo‘naltirish.

### Bosqich 2: APK yaratish

1. **Android WebView ilovasi (mavjud)**
   - URL ni sozlash: ngrok o'rniga **production** yoki **test** server manzili (masalan `https://your-domain.com` yoki `https://your-domain.com/login`).
   - Ilova ichida URL ni o‘zgartirish mumkin bo‘lishi (BuildConfig yoki sozlamalar) — test/production almashtirish oson bo‘ladi.

2. **APK build**
   - Android Studio: **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
   - Debug APK: `android_app/app/build/outputs/apk/debug/app-debug.apk`.
   - Release (Google Play uchun): signing sozlash, keyin **Build → Generate Signed Bundle / APK**.

3. **PWA ni ilova ichida ochish**
   - Agar mobil versiya **asosiy sayt** bo‘lsa: WebView `https://your-server.com/login` ni ochadi.
   - Agar mobil versiya **faqat Agent PWA** bo‘lsa: WebView `/static/pwa/login.html` yoki to‘liq PWA URL ni ochadi (server manzili sozlanadi).

---

## 🎯 Keyingi qadamlar (tavsiya)

1. **Mobil versiya (1–2 hafta)**
   - [ ] Asosiy shablonlarda mobil menyu (hamburger) qo‘shish.
   - [ ] Barcha asosiy sahifalarni mobilda tekshirish va kerak bo‘lsa responsive tuzatishlar.
   - [ ] PWA da API manzilini konfiguratsiyadan o‘qish (env yoki config).

2. **APK (1 kun – mavjud loyiha asosida)**
   - [ ] `MainActivity.kt` da URL ni server manziliga o‘zgartirish (yoki BuildConfig).
   - [ ] Debug APK yig‘ish va telefonda sinash.
   - [ ] Kerak bo‘lsa release APK va signing sozlash.

Agar xohlasangiz, keyingi qadamda mobil menyu (hamburger) va asosiy sahifalarning mobil ko‘rinishini boshlaymiz yoki APK uchun URL sozlash kodini yozamiz.
