"""Completed production must not be hard-deleted: that strands applied stock."""
import asyncio
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

from app.models.database import (
    Base,
    User,
    Warehouse,
    Product,
    Recipe,
    Production,
    Stock,
)
from app.utils.auth import hash_password
from main import delete_production


def _run(coro):
    return asyncio.run(coro)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed(db):
    admin = User(
        username="admin_96ac",
        password_hash=hash_password("test-96ac"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db.add(admin)
    warehouse = Warehouse(name="WH-96ac", code="WH-96ac", is_active=True)
    db.add(warehouse)
    db.flush()
    product = Product(
        name="FG-96ac",
        code="FG-96ac",
        type="tayyor",
        is_active=True,
        purchase_price=1,
        sale_price=2,
    )
    db.add(product)
    db.flush()
    recipe = Recipe(
        product_id=product.id,
        name="R-96ac",
        output_quantity=1,
        is_active=True,
    )
    db.add(recipe)
    db.flush()
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=40)
    db.add(stock)
    db.commit()
    db.refresh(admin)
    db.refresh(stock)
    return admin, warehouse, product, recipe, stock


def test_delete_completed_production_is_rejected_and_stock_kept():
    db = _session()
    admin, warehouse, product, recipe, stock = _seed(db)
    production = Production(
        number=f"PR-96AC-C-{datetime.now().strftime('%H%M%S')}",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        output_warehouse_id=warehouse.id,
        quantity=10,
        status="completed",
        user_id=admin.id,
    )
    db.add(production)
    db.commit()
    db.refresh(production)
    prod_id = production.id
    qty_before = stock.quantity

    result = _run(delete_production(prod_id, db, admin))
    assert isinstance(result, RedirectResponse)
    assert result.status_code == 303
    assert "error=delete" in (result.headers.get("location") or "")

    remaining = db.query(Production).filter(Production.id == prod_id).first()
    assert remaining is not None
    assert remaining.status == "completed"
    db.refresh(stock)
    assert stock.quantity == qty_before
    db.close()


def test_delete_draft_production_still_works():
    db = _session()
    admin, warehouse, product, recipe, stock = _seed(db)
    production = Production(
        number=f"PR-96AC-D-{datetime.now().strftime('%H%M%S')}",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        output_warehouse_id=warehouse.id,
        quantity=10,
        status="draft",
        user_id=admin.id,
    )
    db.add(production)
    db.commit()
    db.refresh(production)
    prod_id = production.id

    result = _run(delete_production(prod_id, db, admin))
    assert isinstance(result, RedirectResponse)
    assert result.status_code == 303
    assert "error=delete" not in (result.headers.get("location") or "")

    remaining = db.query(Production).filter(Production.id == prod_id).first()
    assert remaining is None
    db.close()
