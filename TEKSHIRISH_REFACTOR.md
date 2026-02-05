# main.py refaktor tekshirish

## Bajarilgan ishlar
- Dashboard route'lari `app/routes/dashboard.py` ga ko'chirildi.
- Dublikat `/info/*` bloki `main.py` dan olib tashlandi (route'lar `app/routes/info.py` da).
- `main.py` ~436 qator (avval 5000+ edi).

## Tekshirish (terminalda)

```powershell
cd C:\Users\ELYOR\.cursor\worktrees\business_system\pwp

# 1) Qatorlar soni (~436 bo'lishi kerak)
(Get-Content main.py -Encoding UTF8).Count

# 2) Ilova yuklanadi va route'lar bor
python -c "from main import app; print('OK', len([r for r in app.routes if hasattr(r,'path')]), 'routes')"

# 3) Dashboard va /info faqat izohda, inline yo'q
Select-String -Path main.py -Pattern "DASHBOARDS|/info.*routes" -Encoding UTF8
```

## Kutish
- **OK** va **97 routes** chiqadi.
- `main.py` da "DASHBOARDS" va "/info" faqat izoh sifatida (comment) uchraydi, `@app.get("/dashboard/...")` yoki `@app.get("/info/units"` qatorlari bo'lmasligi kerak.

## Agar IDE da eski (uzun) main.py ko'rinsa
Faylni diskdan qayta yuklang: **File → Revert File** yoki `main.py` ni yopib qayta oching.
