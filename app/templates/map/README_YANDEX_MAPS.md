# 🗺️ Yandex Maps Integration

## ✅ Qo'shildi!

TOTLI HOLVA Business System endi **Yandex Maps** ishlatadi!

### 🎯 Afzalliklar:

1. **🇺🇿 O'zbekiston uchun eng yaxshi**
   - Ko'chalar va manzillar aniq
   - Toshkent shahri to'liq xaritada
   - O'zbek tilida qo'llab-quvvatlash

2. **🆓 Bepul**
   - Oyiga 25,000 so'rov bepul
   - API key talab qilinmaydi (demo rejimda)

3. **🚀 Tez va ishonchli**
   - Yandex serverlari tez
   - Offline rejim qo'llab-quvvatlaydi

4. **📍 Kuchli funksiyalar**
   - Geocoding (manzil → koordinata)
   - Reverse geocoding (koordinata → manzil)
   - Yo'l-yo'riq (routing)
   - Trafik ma'lumotlari

---

## 📁 Fayllar:

- `index.html` - **Yandex Maps versiyasi** (asosiy)
- `index_openstreetmap_backup.html` - OpenStreetMap versiyasi (zaxira)
- `index_yandex.html` - Yandex Maps versiyasi (manba)

---

## 🔧 Qanday ishlaydi:

### 1. **Xarita sahifasi**
URL: `http://10.243.49.144:8080/map`

### 2. **Markerlar:**
- 👤 **Agentlar** - Ko'k rang
- 🚚 **Haydovchilar** - Moviy rang  
- 🏪 **Mijozlar** - Yashil rang
- 🔴 **Offline** - Qizil rang (1 soat+)

### 3. **Filtrlar:**
- Agentlarni ko'rsatish/yashirish
- Haydovchilarni ko'rsatish/yashirish
- Mijozlarni ko'rsatish/yashirish

### 4. **Avtomatik yangilanish:**
- Har 30 sekundda yangilanadi
- Play/Pause tugmasi bilan boshqarish

---

## 🔑 API Key (ixtiyoriy)

Hozirda API key kerak emas, lekin kelajakda qo'shish uchun:

1. Yandex Developer Console ga kiring: https://developer.tech.yandex.ru/
2. Yangi loyiha yarating
3. JavaScript API kalitini oling
4. `index.html` faylida quyidagi qatorni yangilang:

```html
<!-- Eski: -->
<script src="https://api-maps.yandex.ru/2.1/?lang=uz_UZ" type="text/javascript"></script>

<!-- Yangi: -->
<script src="https://api-maps.yandex.ru/2.1/?apikey=YOUR_API_KEY&lang=uz_UZ" type="text/javascript"></script>
```

---

## 📊 Qo'llab-quvvatlanadigan funksiyalar:

✅ Real-time joylashuv kuzatuvi
✅ Agent/Haydovchi/Mijoz markerlari
✅ Offline holat ko'rsatish
✅ Avtomatik yangilanish (30 sek)
✅ Filtrlar
✅ Zoom va pan
✅ Qidiruv
✅ To'liq ekran rejimi
✅ Yo'l-yo'riq tugmasi

---

## 🌐 Til qo'llab-quvvatlashi:

- `uz_UZ` - O'zbek tili (hozirgi)
- `ru_RU` - Rus tili
- `en_US` - Ingliz tili

Tilni o'zgartirish uchun `lang` parametrini o'zgartiring.

---

## 📝 Eslatma:

OpenStreetMap versiyasi `index_openstreetmap_backup.html` faylida saqlab qolindi. Agar Yandex Maps bilan muammo bo'lsa, uni qaytarish mumkin:

```powershell
Copy-Item -Path "app\templates\map\index_openstreetmap_backup.html" -Destination "app\templates\map\index.html" -Force
```

---

**Yaratildi:** 2026-01-26
**Versiya:** 1.0
**Mualliflar:** TOTLI HOLVA Development Team
