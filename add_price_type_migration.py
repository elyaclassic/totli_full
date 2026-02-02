"""Narx turlari jadvali va orders.price_type_id ustunini qo'shish. Bir marta ishga tushiring."""
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root)

from app.models.database import Base, engine, PriceType, DATABASE_URL

def main():
    # 1) Yangi jadvallarni yaratish (price_types, product_prices)
    Base.metadata.create_all(bind=engine)
    print("OK: price_types va product_prices jadvallari tekshirildi/yaratildi.")

    # 2) orders jadvaliga price_type_id ustunini qo'shish (SQLite)
    import sqlite3
    db_path = DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(orders)")
    columns = [row[1] for row in cur.fetchall()]
    if "price_type_id" not in columns:
        cur.execute("ALTER TABLE orders ADD COLUMN price_type_id INTEGER")
        conn.commit()
        print("OK: orders.price_type_id ustuni qo'shildi.")
    else:
        print("OK: orders.price_type_id ustuni allaqachon mavjud.")
    conn.close()

    # 3) Default narx turlari (agar bo'sh bo'lsa)
    from sqlalchemy.orm import Session
    from app.models.database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(PriceType).count() == 0:
            for name, code in [("Chakana", "chakana"), ("Ulgurji", "ulgurji"), ("VIP", "vip")]:
                pt = PriceType(name=name, code=code, is_active=True)
                db.add(pt)
            db.commit()
            print("OK: Default narx turlari qo'shildi (Chakana, Ulgurji, VIP).")
        else:
            print("OK: Narx turlari mavjud.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
