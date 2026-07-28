"""Regression tests: transfer revert invent + purchase expense AP inflation."""
import asyncio
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

import main
from app.models.database import (
    Base,
    Partner,
    Product,
    Purchase,
    PurchaseExpense,
    PurchaseItem,
    Stock,
    User,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferItem,
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


def add_user(db, username="admin", role="admin"):
    user = User(
        username=username,
        full_name=username,
        password_hash="x",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_product(db, code="P1", name="Product"):
    product = Product(code=code, name=name, type="tayyor", is_active=True, purchase_price=0, sale_price=0)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_warehouse(db, code="W1", name="Main"):
    wh = Warehouse(code=code, name=name, is_active=True)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


def add_partner(db, code="S1", name="Supplier", balance=0.0):
    partner = Partner(code=code, name=name, balance=balance, is_active=True, type="supplier")
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def test_transfer_revert_rejects_when_destination_stock_consumed(db, monkeypatch):
    """After transfer + dest consumption, revert must fail — not invent source stock."""
    monkeypatch.setattr(main, "log_audit", lambda *a, **k: None)
    admin = add_user(db)
    product = add_product(db)
    src_wh = add_warehouse(db, "SRC", "Source")
    dest_wh = add_warehouse(db, "DST", "Dest")
    db.add(Stock(warehouse_id=src_wh.id, product_id=product.id, quantity=0))
    db.add(Stock(warehouse_id=dest_wh.id, product_id=product.id, quantity=40))  # 100 transferred, 60 sold
    transfer = WarehouseTransfer(
        number="TR-1",
        date=datetime.now(),
        from_warehouse_id=src_wh.id,
        to_warehouse_id=dest_wh.id,
        status="confirmed",
        user_id=admin.id,
    )
    db.add(transfer)
    db.flush()
    db.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=100))
    db.commit()

    resp = run(main.warehouse_transfer_revert(transfer.id, db=db, current_user=admin))
    assert isinstance(resp, RedirectResponse)
    assert "error=" in (resp.headers.get("location") or "")

    db.refresh(transfer)
    src = db.query(Stock).filter(Stock.warehouse_id == src_wh.id, Stock.product_id == product.id).first()
    dest = db.query(Stock).filter(Stock.warehouse_id == dest_wh.id, Stock.product_id == product.id).first()
    assert transfer.status == "confirmed"
    assert src.quantity == 0
    assert dest.quantity == 40


def test_transfer_revert_succeeds_when_destination_still_holds_qty(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *a, **k: None)
    admin = add_user(db)
    product = add_product(db)
    src_wh = add_warehouse(db, "SRC", "Source")
    dest_wh = add_warehouse(db, "DST", "Dest")
    db.add(Stock(warehouse_id=src_wh.id, product_id=product.id, quantity=0))
    db.add(Stock(warehouse_id=dest_wh.id, product_id=product.id, quantity=100))
    transfer = WarehouseTransfer(
        number="TR-2",
        date=datetime.now(),
        from_warehouse_id=src_wh.id,
        to_warehouse_id=dest_wh.id,
        status="confirmed",
        user_id=admin.id,
    )
    db.add(transfer)
    db.flush()
    db.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=100))
    db.commit()

    resp = run(main.warehouse_transfer_revert(transfer.id, db=db, current_user=admin))
    assert isinstance(resp, RedirectResponse)
    assert "reverted=1" in (resp.headers.get("location") or "")

    db.refresh(transfer)
    src = db.query(Stock).filter(Stock.warehouse_id == src_wh.id, Stock.product_id == product.id).first()
    dest = db.query(Stock).filter(Stock.warehouse_id == dest_wh.id, Stock.product_id == product.id).first()
    assert transfer.status == "draft"
    assert src.quantity == 100
    assert dest.quantity == 0


def test_purchase_confirm_expenses_do_not_inflate_supplier_ap(db, monkeypatch):
    """Landed-cost expenses update product cost but must not increase supplier debt."""
    monkeypatch.setattr(main, "log_audit", lambda *a, **k: None)
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda *a, **k: None)
    admin = add_user(db)
    product = add_product(db)
    warehouse = add_warehouse(db)
    partner = add_partner(db, balance=0.0)
    purchase = Purchase(
        number="P-1",
        partner_id=partner.id,
        warehouse_id=warehouse.id,
        total=1000.0,
        total_expenses=200.0,
        status="draft",
    )
    db.add(purchase)
    db.flush()
    db.add(
        PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=10,
            price=100,
            total=1000,
        )
    )
    db.add(PurchaseExpense(purchase_id=purchase.id, name="Yuk", amount=200))
    db.commit()

    run(main.purchase_confirm(purchase.id, db=db, current_user=admin))
    db.refresh(partner)
    db.refresh(product)
    db.refresh(purchase)
    assert purchase.status == "confirmed"
    assert partner.balance == -1000  # goods only, not -1200
    assert product.purchase_price == 120  # 100 + 200/10 landed cost share

    run(main.purchase_revert(purchase.id, db=db, current_user=admin))
    db.refresh(partner)
    db.refresh(purchase)
    assert purchase.status == "draft"
    assert partner.balance == 0
