# PWA Agent Tracker - Rivojlantirish Rejasi

## 🎯 Maqsad
Agent va driverlar uchun GPS tracking va buyurtmalarni boshqarish ilovasi

## 📱 Texnologiya
- HTML5 + CSS3 + JavaScript
- Service Workers (offline)
- Geolocation API (GPS)
- LocalStorage (offline ma'lumotlar)
- Bootstrap 5 (dizayn)

## 🚀 Bosqichlar

### Kun 1-2: Asosiy Struktura
- [x] Login sahifasi
- [x] Dashboard
- [x] GPS tracking service
- [ ] API integratsiyasi

### Kun 3-4: Funksiyalar
- [ ] Buyurtmalar ro'yxati
- [ ] Mijozlar ro'yxati
- [ ] Lokatsiya yuborish (har 5 daqiqada)
- [ ] Battery level tracking

### Kun 5-6: Offline Rejim
- [ ] Service Worker
- [ ] LocalStorage
- [ ] Sinxronizatsiya

### Kun 7: Test va Deploy
- [ ] Test qilish
- [ ] Bug fixing
- [ ] Production deploy

## 📂 Fayl Tuzilmasi

```
business_system/
├── app/
│   ├── static/
│   │   └── pwa/
│   │       ├── index.html
│   │       ├── login.html
│   │       ├── dashboard.html
│   │       ├── css/
│   │       │   └── app.css
│   │       ├── js/
│   │       │   ├── app.js
│   │       │   ├── gps.js
│   │       │   └── api.js
│   │       ├── manifest.json
│   │       └── sw.js (Service Worker)
│   └── templates/
│       └── pwa/
│           └── index.html
└── main.py (API endpoints)
```

## 🔌 Kerakli API Endpoints

### 1. Authentication
- POST `/api/agent/login` - Agent login
- POST `/api/driver/login` - Driver login

### 2. Location
- POST `/api/agent/location` - Agent lokatsiya yuborish
- POST `/api/driver/location` - Driver lokatsiya yuborish

### 3. Orders
- GET `/api/agent/orders` - Buyurtmalar ro'yxati
- POST `/api/agent/orders/{id}/accept` - Buyurtma qabul qilish

### 4. Partners
- GET `/api/agent/partners` - Mijozlar ro'yxati
- POST `/api/agent/partners` - Yangi mijoz qo'shish

## 📊 Ma'lumotlar Strukturasi

### Agent/Driver Session
```json
{
  "user_id": 1,
  "user_type": "agent",
  "full_name": "Alisher Karimov",
  "token": "...",
  "last_sync": "2026-01-29T16:45:00"
}
```

### Location Data
```json
{
  "latitude": 41.311081,
  "longitude": 69.240562,
  "accuracy": 10,
  "battery": 85,
  "timestamp": "2026-01-29T16:45:00"
}
```

## 🎨 Dizayn
- TOTLI HOLVA branding
- Yashil (#017449) va Sariq (#FFB50D)
- Mobile-first dizayn
- Dark mode (ixtiyoriy)

## ✅ Muvaffaqiyat Mezonlari
- [ ] Login ishlaydi
- [ ] GPS har 5 daqiqada yuboriladi
- [ ] Offline rejimda ishlaydi
- [ ] Battery 10% dan kam bo'lsa GPS to'xtaydi
- [ ] Telefonga o'rnatish mumkin
