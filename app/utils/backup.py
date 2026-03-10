"""
Baza backup: totli_holva.db ni backups/ papkasiga vaqt belgisi bilan nusxalash.
main.py dan avtomatik (kuniga 1 marta) yoki scripts/backup_db.py orqali chaqiriladi.
"""
import os
import shutil
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
    shutil.copy2(db_path, dest)
    return dest
