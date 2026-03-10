"""
Ma'lumotlar bazasini nusxalash: totli_holva.db -> backups/totli_holva_YYYYMMDD_HHMMSS.db
Loyiha ildizidan: python scripts/backup_db.py
"""
import sys
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from app.utils.backup import run_backup

if __name__ == "__main__":
    dest = run_backup()
    print(f"Backup saqlandi: {dest}" if dest else "Baza fayli topilmadi.")
