import sqlite3

from app.utils import backup


def test_run_backup_includes_committed_wal_changes(tmp_path, monkeypatch):
    db_path = tmp_path / "live.db"
    backup_dir = tmp_path / "backups"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("INSERT INTO items (name) VALUES (?)", ("halva",))
        conn.commit()

        monkeypatch.setattr(backup, "get_db_path", lambda: str(db_path))
        monkeypatch.setattr(backup, "get_backup_dir", lambda: str(backup_dir))

        dest = backup.run_backup()

        assert dest is not None
        with sqlite3.connect(dest) as backup_conn:
            rows = backup_conn.execute("SELECT name FROM items").fetchall()
        assert rows == [("halva",)]
    finally:
        conn.close()
