"""productions jadvaliga machine_id va operator_id qo'shadi."""
import os
import sqlite3

_root = os.path.dirname(os.path.abspath(__file__))
_db_path = os.path.join(_root, "totli_holva.db")

if not os.path.exists(_db_path):
    print(f"Baza topilmadi: {_db_path}")
    exit(1)

conn = sqlite3.connect(_db_path)
cur = conn.cursor()

for col in ("machine_id", "operator_id"):
    cur.execute("PRAGMA table_info(productions)")
    columns = [row[1] for row in cur.fetchall()]
    if col in columns:
        print(f"productions.{col} mavjud.")
    else:
        cur.execute(f"ALTER TABLE productions ADD COLUMN {col} INTEGER REFERENCES {'machines(id)' if col == 'machine_id' else 'employees(id)'}")
        conn.commit()
        print(f"productions.{col} qo'shildi.")
conn.close()
