"""Unchecking Faol must revoke login.

HTML omits an unchecked checkbox. The old Form(True) default treated that
omission as active, so saving the user edit form left a disabled account
able to log in.
"""
from fastapi.testclient import TestClient

from app.models.database import SessionLocal, User
from app.utils.auth import create_session_token, hash_password
from main import app


def _admin_client():
    client = TestClient(app)
    client.cookies.set("session_token", create_session_token(1, "admin"))
    client.cookies.set("csrf_token", "csrf-test")
    return client


def _post_user(client, url, username, is_active=None, password=None):
    data = {"username": username, "full_name": "Probe User", "role": "user", "csrf_token": "csrf-test"}
    if password is not None:
        data["password"] = password
    if is_active is not None:
        data["is_active"] = is_active
    return client.post(url, data=data, headers={"accept": "text/html"}, follow_redirects=False)


def test_unchecked_edit_deactivates_and_blocks_login():
    db = SessionLocal()
    username = "deactivate-probe-e42b"
    user = None
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            db.delete(existing)
            db.commit()
        user = User(
            username=username,
            password_hash=hash_password("secret-e42b"),
            full_name="Probe User",
            role="user",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        client = _admin_client()
        saved = _post_user(client, f"/info/users/edit/{user.id}", username)
        assert saved.status_code == 303, saved.text[:300]
        db.refresh(user)
        assert user.is_active is False

        login = client.post(
            "/login",
            data={"username": username, "password": "secret-e42b"},
            headers={"accept": "text/html"},
        )
        assert login.status_code == 200
        assert "faol emas" in login.text

        reactivated = _post_user(client, f"/info/users/edit/{user.id}", username, is_active="true")
        assert reactivated.status_code == 303, reactivated.text[:300]
        db.refresh(user)
        assert user.is_active is True
    finally:
        if user is not None and user.id is not None:
            row = db.query(User).filter(User.id == user.id).first()
            if row:
                db.delete(row)
                db.commit()
        db.close()


def test_unchecked_add_creates_inactive_user():
    db = SessionLocal()
    username = "inactive-add-probe-e42b"
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            db.delete(existing)
            db.commit()
        client = _admin_client()
        created = _post_user(client, "/info/users/add", username, password="secret-e42b")
        assert created.status_code == 303, created.text[:300]
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.is_active is False

        checked = _post_user(
            client,
            f"/info/users/edit/{user.id}",
            username,
            is_active="on",
        )
        assert checked.status_code == 303
        db.refresh(user)
        assert user.is_active is True
    finally:
        row = db.query(User).filter(User.username == username).first()
        if row:
            db.delete(row)
            db.commit()
        db.close()
