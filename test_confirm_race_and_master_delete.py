"""Regression tests: confirm races and master-data hard-delete data loss."""
import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
    CashRegister,
    Order,
    OrderItem,
    Partner,
    Product,
    Purchase,
    PurchaseItem,
    Stock,
    User,
    Warehouse,
)
from app.routes import info as info_routes


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


def add_user(db, username="admin", role="admin"):
    user = User(username=username, password_hash="x", full_name=username, role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_product(db, code="P1", name="Product", ptype="tayyor"):
    product = Product(
        code=code,
        name=name,
        type=ptype,
        purchase_price=10,
        sale_price=20,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_warehouse(db, code="W1", name="Main"):
    warehouse = Warehouse(code=code, name=name, is_active=True)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def add_partner(db, code="C1", name="Customer", ptype="customer", balance=0.0):
    partner = Partner(code=code, name=name, type=ptype, balance=balance, is_active=True)
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def test_sales_confirm_double_submit_does_not_double_subtract(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    partner = add_partner(db)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    db.commit()

    order = Order(
        number="SALE-RACE-1",
        type="sale",
        partner_id=partner.id,
        warehouse_id=warehouse.id,
        user_id=user.id,
        status="draft",
        subtotal=140,
        total=140,
    )
    db.add(order)
    db.commit()
    db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=7, price=20, total=140))
    db.commit()

    run(main.sales_confirm(order.id, db=db, current_user=user))
    run(main.sales_confirm(order.id, db=db, current_user=user))

    db.refresh(order)
    stock = db.query(Stock).filter(
        Stock.warehouse_id == warehouse.id, Stock.product_id == product.id
    ).first()
    assert order.status == "completed"
    assert stock.quantity == 3


def test_sales_confirm_atomic_claim_allows_only_one_winner(db):
    warehouse = add_warehouse(db)
    product = add_product(db)
    partner = add_partner(db)
    order = Order(
        number="SALE-CLAIM-1",
        type="sale",
        partner_id=partner.id,
        warehouse_id=warehouse.id,
        status="draft",
        total=0,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    Session = sessionmaker(bind=db.get_bind())
    s1, s2 = Session(), Session()
    try:
        c1 = s1.query(Order).filter(
            Order.id == order.id, Order.type == "sale", Order.status == "draft"
        ).update({Order.status: "confirming"}, synchronize_session=False)
        s1.commit()
        c2 = s2.query(Order).filter(
            Order.id == order.id, Order.type == "sale", Order.status == "draft"
        ).update({Order.status: "confirming"}, synchronize_session=False)
        s2.commit()
    finally:
        s1.close()
        s2.close()

    assert c1 == 1
    assert c2 == 0


def test_purchase_confirm_double_submit_does_not_double_post(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    partner = add_partner(db, code="S1", name="Supplier", ptype="supplier", balance=0)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=5))
    db.commit()

    purchase = Purchase(
        number="P-RACE-1",
        partner_id=partner.id,
        warehouse_id=warehouse.id,
        total=200,
        total_expenses=0,
        status="draft",
    )
    db.add(purchase)
    db.commit()
    db.add(
        PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=10,
            price=20,
            total=200,
        )
    )
    db.commit()

    run(main.purchase_confirm(purchase.id, db=db, current_user=user))
    with pytest.raises(HTTPException) as exc:
        # Second confirm must not apply stock/AP again.
        run(main.purchase_confirm(purchase.id, db=db, current_user=user))
    assert exc.value.status_code == 400

    db.refresh(purchase)
    db.refresh(partner)
    stock = db.query(Stock).filter(
        Stock.warehouse_id == warehouse.id, Stock.product_id == product.id
    ).first()
    assert purchase.status == "confirmed"
    assert stock.quantity == 15
    assert partner.balance == -200


def test_warehouse_delete_soft_deletes_and_keeps_stock(db):
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=42))
    db.commit()

    resp = run(info_routes.info_warehouses_delete(warehouse.id, db=db, current_user=user))
    db.refresh(warehouse)
    stock = db.query(Stock).filter(
        Stock.warehouse_id == warehouse.id, Stock.product_id == product.id
    ).first()

    assert warehouse.is_active is False
    assert stock is not None
    assert stock.quantity == 42
    assert db.query(Warehouse).filter(Warehouse.id == warehouse.id).first() is not None
    assert "deactivated=1" in (resp.headers.get("location") or "")


def test_cash_delete_soft_deletes_and_keeps_balance(db):
    user = add_user(db)
    cash = CashRegister(name="Main", balance=1500, is_active=True)
    db.add(cash)
    db.commit()
    db.refresh(cash)

    resp = run(info_routes.info_cash_delete(cash.id, db=db, current_user=user))
    db.refresh(cash)

    assert cash.is_active is False
    assert cash.balance == 1500
    assert db.query(CashRegister).filter(CashRegister.id == cash.id).first() is not None
    assert "deactivated=1" in (resp.headers.get("location") or "")
