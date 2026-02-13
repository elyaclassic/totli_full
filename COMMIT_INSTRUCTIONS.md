# Git Commit Qo'llanmasi

## Muammo
Sandbox cheklovlari tufayli `F:/TOTLI_HOLVA/business_system` papkasiga yozish huquqi yo'q, shuning uchun git commit qilishda muammo yuzaga kelmoqda.

## Yechim

### Variant 1: PowerShell'da commit qilish (Tavsiya etiladi)

```powershell
# 1. PowerShell'ni Administrator sifatida oching
# 2. Quyidagi buyruqlarni bajaring:

cd C:\Users\ELYOR\.cursor\worktrees\business_system\hsy

# 3. Barcha o'zgarishlarni qo'shing
git add -A

# 4. Commit qiling
git commit -m "feat: Exceldan yuklash - bitta hujjatga yozish va avtomatik tasdiqlash, hujjat ko'rinishi 1C uslubida yangilandi"

# 5. Tekshirish
git log --oneline -1
```

### Variant 2: Asosiy worktree'da commit qilish

```powershell
# 1. Asosiy worktree'ga o'ting
cd F:\TOTLI_HOLVA\business_system

# 2. Hsy worktree'dagi o'zgarishlarni ko'chiring
# (yoki o'zgarishlarni qo'lda ko'chiring)

# 3. Commit qiling
git add -A
git commit -m "feat: Exceldan yuklash - bitta hujjatga yozish va avtomatik tasdiqlash, hujjat ko'rinishi 1C uslubida yangilandi"
```

### Variant 3: Patch fayl orqali

Agar `changes.patch` fayli yaratilgan bo'lsa:

```powershell
# 1. Asosiy worktree'ga o'ting
cd F:\TOTLI_HOLVA\business_system

# 2. Patch faylni qo'llang
git apply C:\Users\ELYOR\.cursor\worktrees\business_system\hsy\changes.patch

# 3. Commit qiling
git add -A
git commit -m "feat: Exceldan yuklash - bitta hujjatga yozish va avtomatik tasdiqlash, hujjat ko'rinishi 1C uslubida yangilandi"
```

## Qilingan o'zgarishlar

1. **main.py** - `/warehouse/import` funksiyasi yangilandi:
   - Barcha mahsulotlar bitta `StockAdjustmentDoc` hujjatiga yoziladi
   - Hujjat avtomatik tasdiqlanadi (`status = "confirmed"`)
   - Qoldiqlar yangilanadi va `StockMovement` yozuvlari yaratiladi

2. **app/templates/qoldiqlar/hujjat_form.html** - Hujjat ko'rinishi 1C uslubida yangilandi:
   - Jadval ko'rinishi yaxshilandi (border, hover effektlar)
   - Jami qatori qo'shildi
   - Hujjat ma'lumotlari ko'rsatiladi

3. **app/templates/warehouse/list.html** - Hujjatga link qo'shildi:
   - Import muvaffaqiyatli bo'lganda hujjat raqami va ochish linki ko'rsatiladi

4. **app/models/database.py** - `StockMovement` modeli qo'shildi (allaqachon mavjud)

5. **Migration fayllar** - `add_stock_movement_tracking.py` (yangi)

## Keyingi qadamlar

Commit qilgandan keyin:

1. Barcha worktree'larni yangilash:
   ```powershell
   git worktree list
   # Har bir worktree'da: git pull yoki git reset --hard HEAD
   ```

2. Bitta worktree'da ishlashni ta'minlash:
   - Faqat `hsy` yoki `daj` worktree'da ishlash
   - Boshqa worktree'larni yopish yoki faqat o'qish uchun ishlatish
