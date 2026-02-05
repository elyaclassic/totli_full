"""
Autentifikatsiya va xavfsizlik funksiyalari
"""
import os
import secrets
from datetime import datetime
from typing import Optional
from itsdangerous import URLSafeTimedSerializer
import bcrypt
import hashlib

# Session management (production da SECRET_KEY ni env dan o'rnating)
SECRET_KEY = os.getenv("SECRET_KEY", "totli-holva-secret-key-2026-change-in-production")
if os.getenv("PRODUCTION", "").lower() in ("1", "true", "yes") and "change-in-production" in SECRET_KEY:
    raise RuntimeError("Production rejimida SECRET_KEY ni environment o'zgaruvchisi orqali o'rnating.")
SESSION_SERIALIZER = URLSafeTimedSerializer(SECRET_KEY)
SESSION_MAX_AGE = 86400  # 24 soat (sekundlarda)

def _legacy_hash(password: str) -> str:
    """Eski SHA256 hash (migratsiya)"""
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str) -> str:
    """Parolni hash qilish (bcrypt)"""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolni tekshirish (bcrypt, keyin eski SHA256, keyin oddiy matn - migratsiya)"""
    if not hashed_password:
        return False
    if hashed_password.startswith("$2") or hashed_password.startswith("$2a") or hashed_password.startswith("$2b"):
        pwd_bytes = plain_password.encode("utf-8")[:72]
        try:
            return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
        except Exception:
            return False
    if len(hashed_password) == 64 and all(c in "0123456789abcdef" for c in hashed_password.lower()):
        return _legacy_hash(plain_password) == hashed_password
    # Eski tizimda parol hash qilinmagan saqlangan (migratsiya - keyin bcrypt ga yangilang)
    return plain_password == hashed_password


def create_session_token(user_id: int, user_type: str = "user") -> str:
    """Session token yaratish"""
    data = {
        "user_id": user_id,
        "user_type": user_type,
        "created_at": datetime.now().isoformat()
    }
    return SESSION_SERIALIZER.dumps(data)


def verify_session_token(token: str) -> Optional[dict]:
    """Session token tekshirish"""
    try:
        data = SESSION_SERIALIZER.loads(token, max_age=SESSION_MAX_AGE)
        return data
    except Exception:
        return None


def get_user_from_token(token: str) -> Optional[dict]:
    """Token dan foydalanuvchi ma'lumotlarini olish"""
    return verify_session_token(token)


def generate_csrf_token() -> str:
    """CSRF token yaratish (har sahifa yoki session uchun)"""
    return secrets.token_hex(32)


def verify_csrf_token(received: Optional[str], expected: Optional[str]) -> bool:
    """CSRF token tekshirish (vaqtincha va xavfsiz taqqoslash)"""
    if not expected or not received:
        return False
    return secrets.compare_digest(received.strip(), expected.strip())
