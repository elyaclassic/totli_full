# Xarita Tizimi - Map System

## Hozirgi holat / Current Status
✅ **Yandex Maps** ishlatilmoqda (bepul, API key kerak emas)

## Google Maps'ga o'tish / Switching to Google Maps

### 1. Google Maps API Key Oling

1. **Google Cloud Console'ga kiring:**
   - https://console.cloud.google.com/

2. **Yangi Project yarating:**
   - "New Project" → Nom: "TOTLI HOLVA Maps"

3. **Maps JavaScript API yoqing:**
   - "APIs & Services" → "Library"
   - "Maps JavaScript API" → "Enable"

4. **API Key yarating:**
   - "APIs & Services" → "Credentials"
   - "+ CREATE CREDENTIALS" → "API key"
   - API key'ni nusxalang!

5. **API Key'ni himoyalang:**
   - API key yonida "Edit"
   - "Application restrictions" → "HTTP referrers"
   - Qo'shing: `http://10.243.49.144:8080/*`
   - "API restrictions" → "Maps JavaScript API"
   - "Save"

6. **Billing yoqing:**
   - Credit card kerak
   - Har oyda $200 bepul kredit (28,000 xarita yuklash)

### 2. Konfiguratsiyani O'zgartiring

`app/config/maps_config.py` faylini oching va o'zgartiring:

```python
# Yandex'dan Google'ga o'tish
MAP_PROVIDER = 'google'  # 'yandex' o'rniga 'google'

# API key'ni kiriting
GOOGLE_MAPS_API_KEY = 'YOUR_API_KEY_HERE'
```

### 3. Template'larni Yangilang

Avtomatik yangilanadi - faqat serverni qayta ishga tushiring:

```bash
# Serverni to'xtating (Ctrl+C)
# Qayta ishga tushiring
python -m uvicorn main:app --host 10.243.49.144 --port 8080 --reload
```

## Xarita Provayderlari Taqqoslash

| Xususiyat | Yandex Maps | Google Maps |
|-----------|-------------|-------------|
| **Narx** | ✅ Bepul | ⚠️ $200/oy bepul, keyin to'lov |
| **API Key** | ❌ Kerak emas | ✅ Kerak |
| **O'zbekiston xaritalari** | ✅ Yaxshi | ✅ Eng yaxshi |
| **Global qamrov** | ⚠️ O'rtacha | ✅ Eng yaxshi |
| **Tezlik** | ✅ Tez | ✅ Tez |
| **Funksiyalar** | ✅ Yetarli | ✅ Ko'p |

## Fayllar Tuzilishi

```
app/
├── config/
│   └── maps_config.py          # Xarita konfiguratsiyasi
├── templates/
│   ├── map/
│   │   ├── index.html          # Asosiy xarita sahifasi
│   │   ├── _yandex_map.html    # Yandex Maps template
│   │   ├── _google_map.html    # Google Maps template (tayyor)
│   │   └── README_MAPS.md      # Bu fayl
│   └── supervisor/
│       └── dashboard.html      # Supervayzer xaritasi
└── static/
    └── js/
        └── maps/
            ├── yandex-map.js   # Yandex Maps JavaScript
            └── google-map.js   # Google Maps JavaScript (tayyor)
```

## Muammolarni Hal Qilish

### Xarita ko'rinmayapti
1. Browser console'ni tekshiring (F12)
2. API key to'g'riligini tekshiring
3. Billing yoqilganligini tekshiring (Google uchun)

### Markerlar ko'rinmayapti
1. Ma'lumotlar bazasida lokatsiyalar borligini tekshiring:
   ```bash
   python add_test_locations.py
   ```
2. Console'da "Added agent/driver" xabarlari borligini tekshiring

### API Key xatosi (Google)
1. API key to'g'ri nusxalanganligini tekshiring
2. Maps JavaScript API yoqilganligini tekshiring
3. HTTP referrer to'g'ri sozlanganligini tekshiring

## Qo'shimcha Ma'lumot

- **Yandex Maps API:** https://yandex.com/dev/maps/
- **Google Maps API:** https://developers.google.com/maps
- **Pricing (Google):** https://mapsplatform.google.com/pricing/
