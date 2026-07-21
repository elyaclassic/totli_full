import os
import sqlite3

from app.utils import backup


def test_run_backup_includes_committed_wal_transactions(tmp_path, monkeypatch):
    db_path = tmp_path / "live.db"
    backup_dir = tmp_path / "backups"

    source = sqlite3.connect(db_path)
    try:
        assert source.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        source.execute("CREATE TABLE records (value TEXT NOT NULL)")
        source.execute("INSERT INTO records VALUES ('checkpointed')")
        source.commit()
        source.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        # This committed row remains in the WAL while the live connection is
        # open. Copying only live.db would omit it from the backup.
        source.execute("INSERT INTO records VALUES ('latest')")
        source.commit()
        assert os.path.getsize(f"{db_path}-wal") > 0

        monkeypatch.setattr(backup, "get_db_path", lambda: str(db_path))
        monkeypatch.setattr(backup, "get_backup_dir", lambda: str(backup_dir))

        destination = backup.run_backup()

        with sqlite3.connect(destination) as restored:
            values = restored.execute(
                "SELECT value FROM records ORDER BY rowid"
            ).fetchall()
        assert values == [("checkpointed",), ("latest",)]
        assert not list(backup_dir.glob("*.tmp"))
    finally:
        source.close()
