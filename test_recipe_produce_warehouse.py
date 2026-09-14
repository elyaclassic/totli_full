"""Recipe-detail 'Ishlab chiqarish' must not hardcode warehouse_id=1."""
import os
import re
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app.models import database as dbmod
from app.models.database import (
    Base,
    Product,
    Recipe,
    RecipeItem,
    Unit,
    User,
    Warehouse,
    Production,
)
from app.utils.auth import create_session_token, hash_password

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
dbmod.SessionLocal = TestingSession
Base.metadata.create_all(bind=engine)

import main as mainmod

mainmod.SessionLocal = TestingSession

from fastapi.testclient import TestClient

client = TestClient(mainmod.app)


def _seed():
    db = TestingSession()
    try:
        db.query(Production).delete()
        db.query(RecipeItem).delete()
        db.query(Recipe).delete()
        db.query(Product).delete()
        db.query(Warehouse).delete()
        db.query(Unit).delete()
        db.query(User).delete()
        db.commit()

        user = User(
            username="wh_admin",
            password_hash=hash_password("secret"),
            full_name="Admin",
            role="admin",
            is_active=True,
        )
        db.add(user)
        unit = Unit(code="kg", name="Kilogram")
        db.add(unit)
        db.flush()
        # Dummy first warehouse so id=1 is NOT the intended source/output.
        dummy = Warehouse(code="WH-OLD", name="Eski ombor (id=1 trap)", is_active=True)
        raw = Warehouse(code="WH-RAW", name="Xom ashyo ombori", is_active=True)
        fg = Warehouse(code="WH-FG", name="Tayyor mahsulot ombori", is_active=True)
        db.add_all([dummy, raw, fg])
        db.flush()
        material = Product(
            code="MAT1",
            name="Yong'oq",
            type="hom_ashyo",
            unit_id=unit.id,
            purchase_price=1000,
            is_active=True,
        )
        finished = Product(
            code="FG1",
            name="Holva",
            type="tayyor",
            unit_id=unit.id,
            purchase_price=0,
            is_active=True,
        )
        db.add_all([material, finished])
        db.flush()
        recipe = Recipe(
            name="Holva retsepti",
            product_id=finished.id,
            output_quantity=1,
            is_active=True,
        )
        db.add(recipe)
        db.flush()
        db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
        db.commit()
        return {
            "user_id": user.id,
            "dummy_id": dummy.id,
            "raw_id": raw.id,
            "fg_id": fg.id,
            "recipe_id": recipe.id,
        }
    finally:
        db.close()


def _auth_headers(user_id: int):
    token = create_session_token(user_id, "user")
    return token


def _csrf_pair():
    r = client.get("/login")
    csrf = r.cookies.get("csrf_token") or ""
    if not csrf:
        m = re.search(r'name="csrf-token" content="([^"]+)"', r.text)
        csrf = m.group(1) if m else ""
    return csrf


def test_recipe_detail_template_has_warehouse_selects_not_hardcoded_one():
    src = (ROOT / "app" / "templates" / "production" / "recipe_detail.html").read_text(
        encoding="utf-8"
    )
    assert 'name="warehouse_id" value="1"' not in src
    assert 'name="warehouse_id"' in src
    assert 'name="output_warehouse_id"' in src
    assert "<select" in src


def test_recipe_detail_page_lists_real_warehouses_not_hidden_id_one():
    ids = _seed()
    token = _auth_headers(ids["user_id"])
    client.cookies.set("session_token", token)
    r = client.get(f"/production/recipes/{ids['recipe_id']}")
    assert r.status_code == 200, r.text[:500]
    html = r.text
    assert f'value="{ids["raw_id"]}"' in html
    assert f'value="{ids["fg_id"]}"' in html
    assert 'name="warehouse_id" value="1"' not in html
    assert "<select" in html and 'name="warehouse_id"' in html
    assert 'name="output_warehouse_id"' in html


def test_create_production_uses_selected_warehouses_not_id_one():
    ids = _seed()
    token = _auth_headers(ids["user_id"])
    csrf = _csrf_pair()
    client.cookies.set("session_token", token)
    if csrf:
        client.cookies.set("csrf_token", csrf)
    r = client.post(
        "/production/create",
        data={
            "recipe_id": ids["recipe_id"],
            "warehouse_id": ids["raw_id"],
            "output_warehouse_id": ids["fg_id"],
            "quantity": "10",
            "note": "",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert r.status_code in (303, 302), r.text[:800]
    db = TestingSession()
    try:
        prod = db.query(Production).order_by(Production.id.desc()).first()
        assert prod is not None
        assert prod.warehouse_id == ids["raw_id"]
        assert prod.output_warehouse_id == ids["fg_id"]
        assert prod.warehouse_id != ids["dummy_id"]
        assert prod.output_warehouse_id != ids["dummy_id"]
    finally:
        db.close()


def test_create_production_rejects_missing_warehouse():
    ids = _seed()
    token = _auth_headers(ids["user_id"])
    csrf = _csrf_pair()
    client.cookies.set("session_token", token)
    if csrf:
        client.cookies.set("csrf_token", csrf)
    r = client.post(
        "/production/create",
        data={
            "recipe_id": ids["recipe_id"],
            "warehouse_id": "99999",
            "output_warehouse_id": ids["fg_id"],
            "quantity": "10",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert r.status_code == 400
    db = TestingSession()
    try:
        assert db.query(Production).count() == 0
    finally:
        db.close()
