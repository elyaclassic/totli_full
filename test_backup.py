import os
import sqlite3

from app.utils.backup import run_backup


def test_run_backup_uses_sqlite_snapshot_with_wal(tmp_path):
    db_path = tmp_path / "source.db"
    backup_dir = tmp_path / "backups"

    source = sqlite3.connect(db_path)
    try:
        source.execute("PRAGMA journal_mode=WAL")
        source.execute("PRAGMA wal_autocheckpoint=0")
        source.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        source.execute("INSERT INTO items (name) VALUES (?)", ("committed",))
        source.commit()

        assert os.path.exists(str(db_path) + "-wal")

        backup_path = run_backup(str(db_path), str(backup_dir))
    finally:
        source.close()

    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup.execute("SELECT name FROM items").fetchall() == [("committed",)]
