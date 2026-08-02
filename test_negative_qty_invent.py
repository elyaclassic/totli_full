"""Regression: negative sale/recipe/purchase quantities invent or corrupt stock."""
import asyncio
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

import main
from app.models.database import (
    Base,
    Order,
    OrderItem,
    Partner,
    Product,
    Production,
    ProductionItem,
    Purchase,
    PurchaseItem,
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


def test_sales_add_item_rejects_negative_quantity(db):
    user = User(username="u1", full_name="User", password_hash="x", role="user", is_active=True)
    partner = Partner(name="Klient", code="K1", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    product = Product(code="P1", name="Halva", type="tayyor", is_active=True, sale_price=1000, purchase_price=500)
    db.add_all([user, partner, wh, product])
    db.flush()
    order = Order(
        number="S-TEST-1",
        type="sale",
        partner_id=partner.id,
        warehouse_id=wh.id,
        status="draft",
        date=datetime.now(),
        total=0,
        subtotal=0,
    )
    db.add(order)
    db.commit()

    resp = run(
        main.sales_add_item(
            order_id=order.id,
            product_id=product.id,
            quantity=-10,
            db=db,
            current_user=user,
        )
    )
    assert isinstance(resp, RedirectResponse)
    assert "error=stock" in (resp.headers.get("location") or "")
    db.refresh(order)
    assert list(order.items) == []


def test_sales_confirm_rejects_negative_line_without_inventing(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda *args, **kwargs: None)
    user = User(username="u1", full_name="User", password_hash="x", role="user", is_active=True)
    partner = Partner(name="Klient", code="K1", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    product = Product(code="P2", name="Halva", type="tayyor", is_active=True, sale_price=1000, purchase_price=500)
    db.add_all([user, partner, wh, product])
    db.flush()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=20)
    order = Order(
        number="S-TEST-2",
        type="sale",
        partner_id=partner.id,
        warehouse_id=wh.id,
        status="draft",
        date=datetime.now(),
        total=-5000,
        subtotal=-5000,
    )
    db.add_all([stock, order])
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=-5,
            price=1000,
            total=-5000,
        )
    )
    db.commit()

    resp = run(main.sales_confirm(order_id=order.id, db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    assert "error=stock" in (resp.headers.get("location") or "")

    db.refresh(stock)
    db.refresh(order)
    assert stock.quantity == 20
    assert order.status == "draft"


def test_production_complete_rejects_negative_material_without_inventing(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda *args, **kwargs: None)
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    wh = Warehouse(name="Xom", code="WHX", is_active=True)
    out_wh = Warehouse(name="Tayyor", code="WHT", is_active=True)
    material = Product(code="M1", name="Shakar", type="xom", is_active=True, sale_price=1, purchase_price=2)
    finished = Product(code="F1", name="Holva", type="tayyor", is_active=True, sale_price=10, purchase_price=5)
    db.add_all([user, wh, out_wh, material, finished])
    db.flush()
    recipe = Recipe(name="Holva retsept", product_id=finished.id, output_quantity=1, is_active=True)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    mat_stock = Stock(warehouse_id=wh.id, product_id=material.id, quantity=10)
    fg_stock = Stock(warehouse_id=out_wh.id, product_id=finished.id, quantity=0)
    production = Production(
        number="PR-NEG-1",
        recipe_id=recipe.id,
        warehouse_id=wh.id,
        output_warehouse_id=out_wh.id,
        quantity=10,
        status="draft",
        date=datetime.now(),
        user_id=user.id,
        current_stage=1,
        max_stage=2,
    )
    db.add_all([mat_stock, fg_stock, production])
    db.flush()
    # Direct negative production material (recipe UI is free-text; materials edit allows crafted values)
    db.add(ProductionItem(production_id=production.id, product_id=material.id, quantity=-3))
    db.commit()

    resp = run(main.complete_production(prod_id=production.id, db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    assert "error=insufficient_stock" in (resp.headers.get("location") or "")

    db.refresh(mat_stock)
    db.refresh(fg_stock)
    db.refresh(production)
    assert mat_stock.quantity == 10
    assert fg_stock.quantity == 0
    assert production.status == "draft"


def test_recipe_add_item_rejects_negative_quantity(db):
    user = User(username="u1", full_name="User", password_hash="x", role="user", is_active=True)
    material = Product(code="M2", name="Un", type="xom", is_active=True, sale_price=1, purchase_price=1)
    finished = Product(code="F2", name="Non", type="tayyor", is_active=True, sale_price=5, purchase_price=2)
    db.add_all([user, material, finished])
    db.flush()
    recipe = Recipe(name="Non", product_id=finished.id, output_quantity=1, is_active=True)
    db.add(recipe)
    db.commit()

    resp = run(
        main.add_recipe_item(
            recipe_id=recipe.id,
            product_id=material.id,
            quantity=-5,
            db=db,
            current_user=user,
        )
    )
    assert isinstance(resp, RedirectResponse)
    assert "error=qty" in (resp.headers.get("location") or "")
    assert db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe.id).count() == 0


def test_purchase_add_item_rejects_negative_quantity(db):
    user = User(username="u1", full_name="User", password_hash="x", role="user", is_active=True)
    partner = Partner(name="Ta'minotchi", code="T1", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    product = Product(code="P3", name="Yong'oq", type="xom", is_active=True, sale_price=1, purchase_price=1)
    db.add_all([user, partner, wh, product])
    db.flush()
    purchase = Purchase(
        number="P-TEST-1",
        partner_id=partner.id,
        warehouse_id=wh.id,
        status="draft",
        date=datetime.now(),
        total=0,
    )
    db.add(purchase)
    db.commit()

    resp = run(
        main.purchase_add_item(
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=-8,
            price=100,
            db=db,
            current_user=user,
        )
    )
    assert isinstance(resp, RedirectResponse)
    assert "error=item" in (resp.headers.get("location") or "")
    assert db.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase.id).count() == 0
