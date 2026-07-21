"""
Baza backup: totli_holva.db ni backups/ papkasiga vaqt belgisi bilan nusxalash.
main.py dan avtomatik (kuniga 1 marta) yoki scripts/backup_db.py orqali chaqiriladi.
"""
import os
import sqlite3
import tempfile
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

    # A filesystem copy can miss committed data still stored in SQLite's WAL,
    # or capture the database midway through a write.  SQLite's backup API
    # takes a transactionally consistent snapshot of the live database.
    fd, temp_dest = tempfile.mkstemp(
        prefix=f".{base}_",
        suffix=f"{ext}.tmp",
        dir=backup_dir,
    )
    os.close(fd)
    try:
        with closing(sqlite3.connect(db_path)) as source:
            with closing(sqlite3.connect(temp_dest)) as target:
                source.backup(target)
        os.replace(temp_dest, dest)
    except Exception:
        if os.path.exists(temp_dest):
            os.remove(temp_dest)
        raise

    return dest
