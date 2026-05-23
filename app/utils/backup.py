"""
Baza backup: totli_holva.db ni backups/ papkasiga vaqt belgisi bilan saqlash.
main.py dan avtomatik (kuniga 1 marta) yoki scripts/backup_db.py orqali chaqiriladi.
"""
import os
import sqlite3
from datetime import datetime


def get_db_path():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "totli_holva.db")


def get_backup_dir():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "backups")


_scheduler = None


def _make_backup_path(db_path, backup_dir):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base, ext = os.path.splitext(os.path.basename(db_path))
    return os.path.join(backup_dir, f"{base}_{ts}{ext}")


def _check_backup_integrity(dest):
    with sqlite3.connect(dest) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        raise RuntimeError(f"Backup integrity check failed for {dest}: {result}")


def run_backup(db_path=None, backup_dir=None):
    db_path = db_path or get_db_path()
    if not os.path.isfile(db_path):
        return None
    backup_dir = backup_dir or get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    dest = _make_backup_path(db_path, backup_dir)

    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30) as src:
            with sqlite3.connect(dest) as dst:
                src.backup(dst)
        _check_backup_integrity(dest)
    except Exception:
        if os.path.exists(dest):
            os.remove(dest)
        raise
    return dest


def start_backup_scheduler():
    """Backup scheduler ni bir marta ishga tushiradi."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_backup,
        "interval",
        hours=24,
        id="db_backup",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    print("[Backup] Reja ishga tushdi (har 24 soatda baza backup)")
    return _scheduler


def stop_backup_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
