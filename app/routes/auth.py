"""
Autentifikatsiya — login, logout.
"""
import os
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core import templates
from app.models.database import get_db, User
from app.deps import get_current_user
from app.utils.auth import verify_password, create_session_token

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Login yoki parol noto'g'ri!",
            })
        if not user.is_active:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Sizning hisobingiz faol emas. Administrator bilan bog'laning.",
            })
        token = create_session_token(user.id, user.username)
        use_https = os.getenv("HTTPS", "").lower() in ("1", "true", "yes")
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(
            key="session_token",
            value=token,
            path="/",
            httponly=True,
            max_age=86400,
            samesite="lax",
            secure=use_https,
        )
        return resp
    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Tizimda xatolik: {str(e)}",
        })


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("session_token")
    return resp
