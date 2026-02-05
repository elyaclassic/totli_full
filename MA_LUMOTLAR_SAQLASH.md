# Ma'lumotlar saqlashi

**TOTLI HOLVA** tizimida barcha ma'lumotlar **doimiy saqlanadi**. Server qayta ishga tushsa yoki dasturni yopib qayta ochsangiz ham, kiritilgan ma'lumotlar yo'qolmaydi.

## Qayerda saqlanadi?

- **Baza fayli:** loyiha papkasidagi `totli_holva.db` (SQLite).
- **Aniq joy:** `app/models/database.py` da `_root` — loyiha ildizi; baza fayli `totli_holva.db` shu papkada.
- Server qayerdan ishga tushirilsa ham (masalan `python main.py` yoki `uvicorn main:app`) bitta va shu fayl ishlatiladi.

## Nima saqlanmaydi?

- `init_db()` faqat **jadval yaratadi** (agar ular bo'lmasa). Mavjud jadvallar va ichidagi ma'lumotlar **o'chirilmaydi** va **to'ldirilmaydi**.
- Har safar yangi ma'lumot kiritish shart emas — tovarlar, omborlar, sotuvlar, xodimlar va boshqa barcha yozuvlar saqlanadi.

## Eslatma

- `.gitignore` da `*.db` bor — shuning uchun `totli_holva.db` Git ga yuklanmaydi. Ma'lumotlaringiz faqat sizning kompyuteringizda qoladi.
- Zaxira olish uchun `totli_holva.db` faylini boshqa joyga nusxalashingiz mumkin.

**Xulosa:** Ertaga haqiqiy ma'lumotlarni to'ldirsangiz, ular saqlanadi; keyingi marta dasturni ochganda qayta kiritish shart emas.
