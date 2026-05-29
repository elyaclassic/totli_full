"""
Baza backup: totli_holva.db ni backups/ papkasiga vaqt belgisi bilan nusxalash.
main.py dan avtomatik (kuniga 1 marta) yoki scripts/backup_db.py orqali chaqiriladi.
"""
import os
import sqlite3
from contextlib import closing
from datetime import datetime


def get_db_path():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "totli_holva.db")


def get_backup_dir():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "backups")


def run_backup():
    db_path = get_db_path()
    if not os.path.isfile(db_path):
        return None
    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(os.path.basename(db_path))
    dest = os.path.join(backup_dir, f"{base}_{ts}{ext}")

    # Live SQLite databases must be copied through SQLite so WAL/in-flight pages
    # are included in a consistent snapshot.
    with closing(sqlite3.connect(db_path, timeout=30.0)) as source:
        with closing(sqlite3.connect(dest, timeout=30.0)) as target:
            source.backup(target, pages=1000, sleep=0.1)

    return dest
