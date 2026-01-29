# Google Maps'ga O'tish Qo'llanmasi
# Quick Guide to Switch to Google Maps

## 3 Oddiy Qadam / 3 Simple Steps

### 1️⃣ Google Maps API Key Oling
1. https://console.cloud.google.com/ ga kiring
2. Yangi project yarating: "TOTLI HOLVA Maps"
3. "APIs & Services" → "Library" → "Maps JavaScript API" → "Enable"
4. "Credentials" → "Create Credentials" → "API key"
5. API key'ni nusxalang!

### 2️⃣ Konfiguratsiyani O'zgartiring
`app/config/maps_config.py` faylini oching:

```python
# Bu qatorni o'zgartiring:
MAP_PROVIDER = 'google'  # 'yandex' o'rniga

# API key'ni kiriting:
GOOGLE_MAPS_API_KEY = 'YOUR_API_KEY_HERE'  # Bu yerga
```

### 3️⃣ Serverni Qayta Ishga Tushiring
Terminal'da:
- Ctrl+C (serverni to'xtatish)
- Qayta ishga tushirish (avtomatik bo'ladi)

## ✅ Tayyor!
Xarita endi Google Maps ishlatadi!

---

## Yandex Maps'ga Qaytish
`app/config/maps_config.py`:
```python
MAP_PROVIDER = 'yandex'
```

---

## Qo'shimcha
- Batafsil: `app/templates/map/README_MAPS.md`
- Muammolar: Console'ni tekshiring (F12)
