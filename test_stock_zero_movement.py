"""Regression: /warehouse/stock/{id}/zero must record StockMovement (no silent wipe)."""
import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

from app.models.database import Base, Product, Stock, StockMovement, User, Warehouse
import main


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


def test_warehouse_stock_zero_records_movement_and_zeros_qty(db):
    """Admin zero must set qty=0 via create_stock_movement (audit trail required)."""
    admin = User(
        username="admin",
        full_name="Admin",
        password_hash="x",
        role="admin",
        is_active=True,
    )
    wh = Warehouse(name="Ombor 1", code="W1", is_active=True)
    product = Product(name="Yong'oq", code="P1", type="hom_ashyo", is_active=True)
    db.add_all([admin, wh, product])
    db.commit()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=42.5)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    stock_id = stock.id

    resp = run(main.warehouse_stock_zero(stock_id=stock_id, db=db, current_user=admin))
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 303

    db.expire_all()
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    assert stock is not None
    assert stock.quantity == 0

    movements = (
        db.query(StockMovement)
        .filter(
            StockMovement.warehouse_id == wh.id,
            StockMovement.product_id == product.id,
            StockMovement.document_type == "StockZero",
        )
        .all()
    )
    assert len(movements) == 1
    assert movements[0].quantity_change == -42.5
    assert movements[0].quantity_after == 0
    assert movements[0].operation_type == "adjustment"
    assert movements[0].user_id == admin.id


def test_warehouse_stock_zero_is_noop_when_already_zero(db):
    """Zeroing an already-empty row must not invent a phantom movement."""
    admin = User(
        username="admin2",
        full_name="Admin",
        password_hash="x",
        role="admin",
        is_active=True,
    )
    wh = Warehouse(name="Ombor 2", code="W2", is_active=True)
    product = Product(name="Bodom", code="P2", type="hom_ashyo", is_active=True)
    db.add_all([admin, wh, product])
    db.commit()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=0)
    db.add(stock)
    db.commit()
    stock_id = stock.id

    resp = run(main.warehouse_stock_zero(stock_id=stock_id, db=db, current_user=admin))
    assert isinstance(resp, RedirectResponse)

    assert db.query(StockMovement).count() == 0
    db.expire_all()
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    assert stock.quantity == 0


def test_warehouse_stock_zero_does_not_double_apply(db):
    """Must not pre-zero then call create_stock_movement (would invent negative clamp noise)."""
    admin = User(
        username="admin3",
        full_name="Admin",
        password_hash="x",
        role="admin",
        is_active=True,
    )
    wh = Warehouse(name="Ombor 3", code="W3", is_active=True)
    product = Product(name="Asal", code="P3", type="hom_ashyo", is_active=True)
    db.add_all([admin, wh, product])
    db.commit()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=10)
    db.add(stock)
    db.commit()
    stock_id = stock.id

    run(main.warehouse_stock_zero(stock_id=stock_id, db=db, current_user=admin))
    run(main.warehouse_stock_zero(stock_id=stock_id, db=db, current_user=admin))

    db.expire_all()
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    assert stock.quantity == 0
    # Only the first call should write a movement for the non-zero qty.
    movements = db.query(StockMovement).filter(StockMovement.document_type == "StockZero").all()
    assert len(movements) == 1
    assert movements[0].quantity_change == -10
