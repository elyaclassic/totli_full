"""Regression: empty recipe / non-positive output must not invent finished goods."""
import asyncio
from datetime import datetime
from urllib.parse import unquote

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

import main
from app.models.database import (
    Base,
    Product,
    Production,
    ProductionItem,
    Recipe,
    RecipeItem,
    Stock,
    User,
    Warehouse,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _seed(db, *, output_quantity=1.0, with_material=False, material_qty=2.0):
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    finished = Product(code="FG1", name="Holva", type="tayyor", is_active=True, sale_price=10, purchase_price=5)
    material = Product(code="RM1", name="Yong'oq", type="hom_ashyo", is_active=True, sale_price=1, purchase_price=1)
    db.add_all([user, wh, finished, material])
    db.flush()
    recipe = Recipe(
        name="Bo'sh retsept" if not with_material else "Normal",
        product_id=finished.id,
        output_quantity=output_quantity,
        is_active=True,
    )
    db.add(recipe)
    db.flush()
    if with_material:
        db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=material_qty))
        db.add(Stock(warehouse_id=wh.id, product_id=material.id, quantity=100))
    production = Production(
        number="PR-TEST-1",
        recipe_id=recipe.id,
        warehouse_id=wh.id,
        output_warehouse_id=wh.id,
        quantity=10,
        status="draft",
        current_stage=1,
        max_stage=2,
        user_id=user.id,
        date=datetime.now(),
    )
    db.add(production)
    db.flush()
    if with_material:
        db.add(
            ProductionItem(
                production_id=production.id,
                product_id=material.id,
                quantity=material_qty * production.quantity,
            )
        )
    db.commit()
    return user, wh, finished, material, recipe, production


def test_empty_recipe_complete_does_not_invent_finished_goods(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda *args, **kwargs: None)
    user, wh, finished, material, recipe, production = _seed(db, with_material=False)

    err = main._do_complete_production_stock(db, production, recipe)
    assert isinstance(err, RedirectResponse)
    location = unquote(err.headers.get("location") or "")
    assert "no_materials" in location

    fg = db.query(Stock).filter(Stock.warehouse_id == wh.id, Stock.product_id == finished.id).first()
    assert fg is None or (fg.quantity or 0) == 0


def test_all_zero_materials_complete_does_not_invent(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda *args, **kwargs: None)
    user, wh, finished, material, recipe, production = _seed(db, with_material=True, material_qty=2.0)
    for pi in production.production_items:
        pi.quantity = 0
    db.commit()

    err = main._do_complete_production_stock(db, production, recipe)
    assert isinstance(err, RedirectResponse)
    location = unquote(err.headers.get("location") or "")
    assert "no_materials" in location

    fg = db.query(Stock).filter(Stock.warehouse_id == wh.id, Stock.product_id == finished.id).first()
    assert fg is None or (fg.quantity or 0) == 0
    rm = db.query(Stock).filter(Stock.warehouse_id == wh.id, Stock.product_id == material.id).first()
    assert rm.quantity == 100


def test_negative_output_quantity_rejected_on_complete(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda *args, **kwargs: None)
    user, wh, finished, material, recipe, production = _seed(
        db, output_quantity=-1.0, with_material=True, material_qty=1.0
    )

    err = main._do_complete_production_stock(db, production, recipe)
    assert isinstance(err, RedirectResponse)
    location = unquote(err.headers.get("location") or "")
    assert "error=qty" in location or "Chiqish" in location

    fg = db.query(Stock).filter(Stock.warehouse_id == wh.id, Stock.product_id == finished.id).first()
    assert fg is None or (fg.quantity or 0) == 0
    rm = db.query(Stock).filter(Stock.warehouse_id == wh.id, Stock.product_id == material.id).first()
    assert rm.quantity == 100


def test_add_recipe_rejects_non_positive_output_quantity(db):
    finished = Product(code="FG2", name="Non", type="tayyor", is_active=True, sale_price=1, purchase_price=1)
    user = User(username="u1", full_name="U", password_hash="x", role="admin", is_active=True)
    db.add_all([finished, user])
    db.commit()

    resp = run(
        main.add_recipe(
            request=None,
            name="Bad",
            product_id=finished.id,
            output_quantity=-2,
            description="",
            db=db,
            current_user=user,
        )
    )
    assert isinstance(resp, RedirectResponse)
    assert "error=qty" in (resp.headers.get("location") or "")
    assert db.query(Recipe).filter(Recipe.name == "Bad").first() is None
