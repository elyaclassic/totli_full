import os
import sqlite3

from app.utils.backup import run_backup


def test_run_backup_creates_consistent_sqlite_snapshot_during_write(tmp_path):
    db_path = tmp_path / "live.db"
    backup_dir = tmp_path / "backups"

    writer = sqlite3.connect(db_path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        writer.execute("INSERT INTO items (name) VALUES ('committed')")
        writer.commit()

        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO items (name) VALUES ('uncommitted')")

        backup_path = run_backup(str(db_path), str(backup_dir))
    finally:
        writer.rollback()
        writer.close()

    assert backup_path is not None
    assert os.path.isfile(backup_path)

    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        rows = backup.execute("SELECT name FROM items ORDER BY id").fetchall()

    assert rows == [("committed",)]


def test_run_backup_returns_none_when_database_is_missing(tmp_path):
    backup_path = run_backup(str(tmp_path / "missing.db"), str(tmp_path / "backups"))

    assert backup_path is None
