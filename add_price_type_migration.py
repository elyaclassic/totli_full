"""
orders jadvaliga price_type_id ustunini qo'shadi (agar bo'lmasa).
Baza: totli_holva.db (loyiha ildizida).
"""
import os
import sqlite3

_root = os.path.dirname(os.path.abspath(__file__))
_db_path = os.path.join(_root, "totli_holva.db")

if not os.path.exists(_db_path):
    print(f"Baza topilmadi: {_db_path}")
    exit(1)

conn = sqlite3.connect(_db_path)
cur = conn.cursor()

# orders jadvalidagi ustunlarni tekshirish
cur.execute("PRAGMA table_info(orders)")
columns = [row[1] for row in cur.fetchall()]

if "price_type_id" in columns:
    print("orders.price_type_id allaqachon mavjud.")
else:
    cur.execute("ALTER TABLE orders ADD COLUMN price_type_id INTEGER REFERENCES price_types(id)")
    conn.commit()
    print("orders.price_type_id muvaffaqiyatli qo'shildi.")

conn.close()
