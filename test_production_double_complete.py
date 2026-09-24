"""Completing a production order twice must not post inventory twice."""
import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
    Product,
    Production,
    ProductionItem,
    Recipe,
    RecipeItem,
    RecipeStage,
    Stock,
    User,
    Warehouse,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def run(coro):
    return asyncio.run(coro)


def _seed(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    material = Product(code="MAT", name="Flour", type="hom_ashyo", purchase_price=10, sale_price=0, is_active=True)
    finished = Product(code="FG", name="Halva", type="tayyor", purchase_price=0, sale_price=20, is_active=True)
    warehouse = Warehouse(code="W1", name="Main", is_active=True)
    db.add_all([user, material, finished, warehouse])
    db.commit()
    db.add(Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=10))
    recipe = Recipe(name="Halva", product_id=finished.id, output_quantity=1, is_active=True)
    db.add(recipe)
    db.commit()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=4))
    db.add(RecipeStage(recipe_id=recipe.id, stage_number=1, name="Mix"))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        output_warehouse_id=warehouse.id,
        quantity=1,
        status="draft",
        current_stage=1,
        max_stage=1,
    )
    db.add(production)
    db.commit()
    db.add(ProductionItem(production_id=production.id, product_id=material.id, quantity=4))
    db.commit()
    db.refresh(production)
    return user, production, material, finished, warehouse


def _qty(db, warehouse_id, product_id):
    stock = db.query(Stock).filter(
        Stock.warehouse_id == warehouse_id,
        Stock.product_id == product_id,
    ).first()
    return stock.quantity if stock else 0


def test_complete_production_second_post_does_not_move_stock(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    user, production, material, finished, warehouse = _seed(db)

    first = run(main.complete_production(production.id, db=db, current_user=user))
    assert first.status_code == 303
    db.refresh(production)
    assert production.status == "completed"
    material_after = _qty(db, warehouse.id, material.id)
    finished_after = _qty(db, warehouse.id, finished.id)
    assert material_after == 6
    assert finished_after > 0

    second = run(main.complete_production(production.id, db=db, current_user=user))
    assert second.status_code == 303
    db.refresh(production)
    assert production.status == "completed"
    assert _qty(db, warehouse.id, material.id) == material_after
    assert _qty(db, warehouse.id, finished.id) == finished_after


def test_last_stage_resubmit_does_not_move_stock(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    user, production, material, finished, warehouse = _seed(db)

    first = run(main.complete_production_stage(
        production.id, stage_number=1, db=db, current_user=user,
    ))
    assert first.status_code == 303
    db.refresh(production)
    assert production.status == "completed"
    material_after = _qty(db, warehouse.id, material.id)
    finished_after = _qty(db, warehouse.id, finished.id)

    second = run(main.complete_production_stage(
        production.id, stage_number=1, db=db, current_user=user,
    ))
    assert second.status_code == 303
    assert _qty(db, warehouse.id, material.id) == material_after
    assert _qty(db, warehouse.id, finished.id) == finished_after


def test_complete_cancelled_production_does_not_move_stock(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    user, production, material, finished, warehouse = _seed(db)
    production.status = "cancelled"
    db.commit()

    resp = run(main.complete_production(production.id, db=db, current_user=user))
    assert resp.status_code == 303
    db.refresh(production)
    assert production.status == "cancelled"
    assert _qty(db, warehouse.id, material.id) == 10
    assert _qty(db, warehouse.id, finished.id) == 0


def test_failed_complete_keeps_order_editable(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    user, production, material, finished, warehouse = _seed(db)
    stock = db.query(Stock).filter(Stock.product_id == material.id).first()
    stock.quantity = 1
    db.commit()

    resp = run(main.complete_production(production.id, db=db, current_user=user))
    assert resp.status_code == 303
    assert "insufficient_stock" in resp.headers["location"]
    db.refresh(production)
    assert production.status == "draft"
    assert _qty(db, warehouse.id, material.id) == 1
