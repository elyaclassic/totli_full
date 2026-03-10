"""
Audit log: kim, qachon, qanday amal bajardi.
Yozuvlar logs/audit.log fayliga qo'shiladi (CSV-ga o'xshash).
"""
import os
from datetime import datetime
from typing import Optional


def _log_dir():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "logs")


def log_audit(
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    detail: Optional[str] = None,
):
    """
    Audit yozuvini qo'shish.
    action: login_success, logout, sale_confirm, purchase_confirm, order_create, ...
    detail: qo'shimcha ma'lumot (masalan hujjat raqami).
    """
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "audit.log")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uid = str(user_id) if user_id is not None else ""
    uname = (username or "").replace("|", ",").replace("\n", " ")
    act = (action or "").replace("|", ",").replace("\n", " ")
    det = (detail or "").replace("|", ",").replace("\n", " ")
    line = f"{ts}|{uid}|{uname}|{act}|{det}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
