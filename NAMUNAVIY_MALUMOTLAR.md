# NAMUNAVIY MA'LUMOTLAR RO'YXATI
# LIST OF SAMPLE/TEST DATA

Ushbu faylda tizimda mavjud bo'lgan barcha namunaviy (test) ma'lumotlar ro'yxati keltirilgan.
Siz ularni haqiqiy ma'lumotlar bilan almashtirish uchun foydalanishingiz mumkin.

---

## 1. AGENTLAR (AGENTS)

**Jami: 4 ta**

### Agent #1
- **ID:** 1
- **Ism:** Alisher Karimov
- **Telefon:** +998901111111
- **Hudud:** Toshkent shahri
- **Lokatsiyalar:** 6 ta test lokatsiya

### Agent #2
- **ID:** 2
- **Ism:** Botir Yusupov
- **Telefon:** +998902222222
- **Hudud:** Toshkent viloyati
- **Lokatsiyalar:** 6 ta test lokatsiya

### Agent #3
- **ID:** 3
- **Ism:** Sardor Alimov
- **Telefon:** +998903333333
- **Hudud:** Samarqand
- **Lokatsiyalar:** 6 ta test lokatsiya

### Agent #4
- **ID:** 4
- **Ism:** Jamshid Raximov
- **Telefon:** +998904444444
- **Hudud:** Buxoro
- **Lokatsiyalar:** 6 ta test lokatsiya

**O'zgartirish uchun:**
- Web interfeys: http://10.243.49.144:8080/agents
- Yoki to'g'ridan-to'g'ri database'da

---

## 2. HAYDOVCHILAR (DRIVERS)

**Jami: 3 ta**

### Driver #1
- **ID:** 1
- **Ism:** Rustam Qodirov
- **Telefon:** +998905555555
- **Mashina raqami:** 01A123BC
- **Lokatsiyalar:** 11 ta test lokatsiya

### Driver #2
- **ID:** 2
- **Ism:** Odil Nazarov
- **Telefon:** +998906666666
- **Mashina raqami:** 01B456DE
- **Lokatsiyalar:** 11 ta test lokatsiya

### Driver #3
- **ID:** 3
- **Ism:** Shuhrat Toshmatov
- **Telefon:** +998907777777
- **Mashina raqami:** 01C789FG
- **Lokatsiyalar:** 11 ta test lokatsiya

**O'zgartirish uchun:**
- Web interfeys: http://10.243.49.144:8080/drivers
- Yoki to'g'ridan-to'g'ri database'da

---

## 3. MIJOZLAR (PARTNERS)

**Jami: 2 ta namunaviy mijoz**

### Partner #1
- **ID:** 1
- **Nomi:** Namunaviy mijoz
- **Telefon:** +998901234567
- **Lokatsiya:** 1 ta test lokatsiya

### Partner #2
- **ID:** 2
- **Nomi:** Namunaviy yetkazib beruvchi
- **Telefon:** +998909876543
- **Lokatsiya:** Yo'q

**O'zgartirish uchun:**
- Web interfeys: http://10.243.49.144:8080/partners
- Yoki to'g'ridan-to'g'ri database'da

---

## 4. KATEGORIYALAR (CATEGORIES)

**Jami: 5 ta**

1. **Halva** (ID: 1)
2. **Konfetlar** (ID: 2)
3. **Shirinliklar** (ID: 3)
4. **Xom ashyo** (ID: 4)
5. **Qadoqlash materiallari** (ID: 5)

**O'zgartirish uchun:**
- Web interfeys: http://10.243.49.144:8080/categories

---

## 5. MAHSULOTLAR (PRODUCTS)

**Jami: 5 ta**

1. **Halva oddiy** (ID: 1)
2. **Halva shokoladli** (ID: 2)
3. **Halva yong'oqli** (ID: 3)
4. **Shakar** (ID: 4) - Xom ashyo
5. **Kunjut** (ID: 5) - Xom ashyo

**O'zgartirish uchun:**
- Web interfeys: http://10.243.49.144:8080/products

---

## 6. OMBORLAR (WAREHOUSES)

**Jami: 3 ta**

1. **Asosiy ombor** (ID: 1)
2. **Tayyor mahsulot** (ID: 2)
3. **Xom ashyo ombori** (ID: 3)

**O'zgartirish uchun:**
- Web interfeys: http://10.243.49.144:8080/warehouses

---

## 7. FOYDALANUVCHILAR (USERS)

**Jami: 1 ta**

### User #1
- **ID:** 1
- **Username:** admin
- **Ism:** Administrator
- **Rol:** admin
- **Parol:** admin (o'zgartirish tavsiya etiladi!)

**O'zgartirish uchun:**
- Web interfeys: http://10.243.49.144:8080/users
- Parolni o'zgartirish: Profil sahifasi

---

## 8. TEST LOKATSIYALAR

### Agent Lokatsiyalari
- Jami: 24 ta test lokatsiya
- Har bir agent uchun: 6 ta
- Toshkent atrofida tasodifiy koordinatalar

### Driver Lokatsiyalari
- Jami: 33 ta test lokatsiya
- Har bir driver uchun: 11 ta
- Toshkent atrofida tasodifiy koordinatalar

### Partner Lokatsiyalari
- Jami: 1 ta test lokatsiya

**O'chirish uchun:**
```sql
DELETE FROM agent_locations;
DELETE FROM driver_locations;
DELETE FROM partner_locations WHERE partner_id IN (1, 2);
```

---

## HAQIQIY MA'LUMOTLAR BILAN ALMASHTIRISH TARTIBI

### 1. Agentlarni Almashtirish
1. Web interfeys orqali: http://10.243.49.144:8080/agents
2. Har bir agentni tahrirlang yoki yangi agent qo'shing
3. Test agentlarni o'chiring (agar kerak bo'lsa)

### 2. Haydovchilarni Almashtirish
1. Web interfeys orqali: http://10.243.49.144:8080/drivers
2. Har bir driverni tahrirlang yoki yangi driver qo'shing
3. Test driverlarni o'chiring (agar kerak bo'lsa)

### 3. Mijozlarni Almashtirish
1. Web interfeys orqali: http://10.243.49.144:8080/partners
2. "Namunaviy mijoz" va "Namunaviy yetkazib beruvchi"ni o'chiring
3. Haqiqiy mijozlarni qo'shing

### 4. Mahsulotlarni Almashtirish
1. Web interfeys orqali: http://10.243.49.144:8080/products
2. Test mahsulotlarni o'chiring yoki tahrirlang
3. Haqiqiy mahsulotlarni qo'shing

### 5. Test Lokatsiyalarni O'chirish
```bash
# Database'ga kiring
sqlite3 totli_holva.db

# Test lokatsiyalarni o'chirish
DELETE FROM agent_locations;
DELETE FROM driver_locations;
DELETE FROM partner_locations WHERE partner_id IN (1, 2);

# Chiqish
.exit
```

---

## MUHIM ESLATMALAR

⚠️ **DIQQAT:**
1. Test ma'lumotlarni o'chirishdan oldin backup oling!
2. Admin parolini o'zgartiring!
3. Haqiqiy ma'lumotlarni kiritishdan oldin test qiling!

✅ **TAVSIYALAR:**
1. Birinchi navbatda kategoriya va mahsulotlarni to'ldiring
2. Keyin agentlar va driverlarni qo'shing
3. Oxirida mijozlarni qo'shing
4. Lokatsiyalar avtomatik ravishda mobil ilovadan kelib tushadi

---

**Oxirgi yangilanish:** 2026-01-29
**Versiya:** 1.0
