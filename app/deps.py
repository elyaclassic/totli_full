"""
Umumiy dependency lar — get_db, get_current_user, require_auth, require_admin.
Routerlar shu moduldan import qiladi.
"""
from typing import Optional
from fastapi import Depends, Cookie
from sqlalchemy.orm import Session

from app.models.database import get_db, User
from app.utils.auth import get_user_from_token


def get_current_user(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Cookie dan foydalanuvchini olish"""
    if not session_token:
        return None
    user_data = get_user_from_token(session_token)
    if not user_data:
        return None
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return None
    return user


def require_auth(current_user: Optional[User] = Depends(get_current_user)) -> Optional[User]:
    """Login talab qilish"""
    return current_user


def require_admin(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """Faqat admin"""
    if not current_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Login talab qilindi")
    if current_user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Faqat administrator uchun ruxsat")
    return current_user
