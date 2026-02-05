"""employees jadvaliga birth_date ustunini qo'shadi (agar bo'lmasa)."""
import os
import sqlite3

_root = os.path.dirname(os.path.abspath(__file__))
_db_path = os.path.join(_root, "totli_holva.db")

if not os.path.exists(_db_path):
    print(f"Baza topilmadi: {_db_path}")
    exit(1)

conn = sqlite3.connect(_db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(employees)")
columns = [row[1] for row in cur.fetchall()]

if "birth_date" in columns:
    print("employees.birth_date allaqachon mavjud.")
else:
    cur.execute("ALTER TABLE employees ADD COLUMN birth_date DATE")
    conn.commit()
    print("employees.birth_date qo'shildi.")
conn.close()
