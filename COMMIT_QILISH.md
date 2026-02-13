# Git Commit Qilish - Qadam-baqadam Ko'rsatma

## 1-qadam: PowerShell'ni ochish

1. **Windows Start** tugmasini bosing
2. **PowerShell** yozing
3. **Windows PowerShell** ni **o'ng tugma bilan bosing** va **"Run as Administrator"** ni tanlang
4. PowerShell oynasi ochiladi

## 2-qadam: Worktree papkasiga o'tish

PowerShell'da quyidagi buyruqni kiriting:

```powershell
cd C:\Users\ELYOR\.cursor\worktrees\business_system\hsy
```

Enter tugmasini bosing.

## 3-qadam: Git holatini tekshirish

```powershell
git status
```

Bu buyruq barcha o'zgarishlarni ko'rsatadi.

## 4-qadam: O'zgarishlarni qo'shish (Staging)

**Variant A: Barcha o'zgarishlarni qo'shish (tavsiya etiladi)**

```powershell
git add .
```

Yoki faqat muhim fayllarni qo'shish:

```powershell
git add main.py
git add app/models/database.py
git add app/templates/qoldiqlar/hujjat_form.html
git add app/templates/warehouse/list.html
git add alembic/versions/add_stock_movement_tracking.py
git add .gitattributes
```

## 5-qadam: Commit qilish

```powershell
git commit -m "feat: Exceldan yuklash - bitta hujjatga yozish va avtomatik tasdiqlash, hujjat ko'rinishi 1C uslubida yangilandi"
```

## 6-qadam: Tekshirish

```powershell
git log --oneline -1
```

Bu buyruq oxirgi commit'ni ko'rsatadi. Agar yangi commit ko'rsatilsa, muvaffaqiyatli!

## Muammo bo'lsa

### Agar "Permission denied" xatosi bo'lsa:

1. **Lock faylni o'chirish:**
```powershell
Remove-Item "F:\TOTLI_HOLVA\business_system\.git\worktrees\hsy\index.lock" -Force -ErrorAction SilentlyContinue
```

2. **Git jarayonlarini to'xtatish:**
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*git*"} | Stop-Process -Force
```

3. **Qayta urinib ko'rish:**
```powershell
git add .
git commit -m "feat: Exceldan yuklash - bitta hujjatga yozish va avtomatik tasdiqlash, hujjat ko'rinishi 1C uslubida yangilandi"
```

### Agar "LF will be replaced by CRLF" ogohlantirishlari bo'lsa:

Bu normal! Bu faqat ogohlantirish, muammo emas. `.gitattributes` fayli bu ogohlantirishlarni kamaytiradi.

## Qo'shimcha ma'lumot

- **Commit xabari:** Qisqa va aniq bo'lishi kerak
- **Ko'p fayl:** Agar ko'p fayl bo'lsa, `git add .` ishlatish mumkin
- **Tekshirish:** Har doim `git status` va `git log` bilan tekshiring

## Keyingi qadamlar

Commit qilgandan keyin:

1. **Barcha worktree'larni yangilash**
2. **Bitta worktree'da ishlashni ta'minlash**
