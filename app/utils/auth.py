"""
Autentifikatsiya va xavfsizlik funksiyalari
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from itsdangerous import URLSafeTimedSerializer
import os

# Session management
SECRET_KEY = os.getenv("SECRET_KEY", "totli-holva-secret-key-2026-change-in-production")
SESSION_SERIALIZER = URLSafeTimedSerializer(SECRET_KEY)
SESSION_MAX_AGE = 86400  # 24 soat (sekundlarda)


def hash_password(password: str) -> str:
    """Parolni hash qilish (SHA256)"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolni tekshirish"""
    return hash_password(plain_password) == hashed_password


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
