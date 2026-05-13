"""
Baza backup: totli_holva.db ni backups/ papkasiga vaqt belgisi bilan nusxalash.
main.py dan avtomatik (kuniga 1 marta) yoki scripts/backup_db.py orqali chaqiriladi.
"""
import os
import sqlite3
import tempfile
from datetime import datetime


def get_db_path():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "totli_holva.db")


def get_backup_dir():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "backups")


def _unique_backup_path(backup_dir, base, ext):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = os.path.join(backup_dir, f"{base}_{ts}{ext}")
    if not os.path.exists(candidate):
        return candidate
    for index in range(1, 1000):
        candidate = os.path.join(backup_dir, f"{base}_{ts}_{index}{ext}")
        if not os.path.exists(candidate):
            return candidate
    raise RuntimeError("Backup fayl nomi yaratib bo'lmadi")


def run_backup(db_path=None, backup_dir=None):
    db_path = db_path or get_db_path()
    if not os.path.isfile(db_path):
        return None
    backup_dir = backup_dir or get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(db_path))
    ext = ext or ".db"
    dest = _unique_backup_path(backup_dir, base, ext)
    fd, tmp_path = tempfile.mkstemp(prefix=f".{base}_", suffix=ext, dir=backup_dir)
    os.close(fd)
    try:
        source_uri = f"file:{os.path.abspath(db_path)}?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(tmp_path) as target:
            source.backup(target)
        os.replace(tmp_path, dest)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
    return dest
