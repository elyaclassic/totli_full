"""Regression tests for purchase total corruption, balance-doc revert wipe, and sales AR."""
import asyncio
from inspect import signature

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
    CashBalanceDoc,
    CashBalanceDocItem,
    CashRegister,
    Order,
    OrderItem,
    Partner,
    PartnerBalanceDoc,
    PartnerBalanceDocItem,
    Product,
    Purchase,
    PurchaseItem,
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


def add_user(db, username="admin", role="admin"):
    user = User(username=username, password_hash="x", full_name=username, role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_product(db, code="P1", name="Sugar"):
    product = Product(code=code, name=name, type="tayyor", purchase_price=10, sale_price=20, is_active=True)
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


def add_partner(db, code="C1", name="Customer", balance=0.0):
    partner = Partner(code=code, name=name, type="customer", balance=balance, is_active=True)
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def test_purchase_add_item_requires_auth_and_draft_and_does_not_double_count(db):
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    purchase = Purchase(
        number="PUR-1",
        warehouse_id=warehouse.id,
        partner_id=None,
        user_id=user.id,
        total=0,
        status="draft",
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    params = signature(main.purchase_add_item).parameters
    assert "current_user" in params

    run(
        main.purchase_add_item(
            purchase.id,
            product_id=product.id,
            quantity=2,
            price=100,
            db=db,
            current_user=user,
        )
    )
    db.refresh(purchase)
    assert purchase.total == 200
    assert db.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase.id).count() == 1

    run(
        main.purchase_add_item(
            purchase.id,
            product_id=product.id,
            quantity=1,
            price=50,
            db=db,
            current_user=user,
        )
    )
    db.refresh(purchase)
    assert purchase.total == 250

    purchase.status = "confirmed"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        run(
            main.purchase_add_item(
                purchase.id,
                product_id=product.id,
                quantity=1,
                price=10,
                db=db,
                current_user=user,
            )
        )
    assert exc.value.status_code == 400
    assert db.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase.id).count() == 2


def test_partner_balance_doc_revert_preserves_later_purchase_debt(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    admin = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    partner = add_partner(db, balance=0)

    doc = PartnerBalanceDoc(number="KNT-1", user_id=admin.id, status="draft")
    db.add(doc)
    db.commit()
    db.add(PartnerBalanceDocItem(doc_id=doc.id, partner_id=partner.id, balance=1000))
    db.commit()

    run(main.qoldiqlar_kontragent_hujjat_tasdiqlash(doc.id, db=db, current_user=admin))
    db.refresh(partner)
    assert partner.balance == 1000

    purchase = Purchase(
        number="PUR-BAL-1",
        warehouse_id=warehouse.id,
        partner_id=partner.id,
        user_id=admin.id,
        total=300,
        status="draft",
    )
    db.add(purchase)
    db.commit()
    db.add(
        PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=3,
            price=100,
            total=300,
        )
    )
    db.commit()

    run(main.purchase_confirm(purchase.id, db=db, current_user=admin))
    db.refresh(partner)
    assert partner.balance == 700  # 1000 opening - 300 purchase debt

    run(main.qoldiqlar_kontragent_hujjat_revert(doc.id, db=db, current_user=admin))
    db.refresh(partner)
    # Revert undoes +1000 opening set, keeps -300 purchase effect → -300
    assert partner.balance == -300


def test_cash_balance_doc_revert_preserves_later_manual_change(db):
    admin = add_user(db)
    cash = CashRegister(name="Main cash", balance=100, is_active=True)
    db.add(cash)
    db.commit()
    db.refresh(cash)

    doc = CashBalanceDoc(number="KLD-1", user_id=admin.id, status="draft")
    db.add(doc)
    db.commit()
    db.add(CashBalanceDocItem(doc_id=doc.id, cash_register_id=cash.id, balance=500))
    db.commit()

    run(main.qoldiqlar_kassa_hujjat_tasdiqlash(doc.id, db=db, current_user=admin))
    db.refresh(cash)
    assert cash.balance == 500

    cash.balance = 450  # later ledger movement
    db.commit()

    run(main.qoldiqlar_kassa_hujjat_revert(doc.id, db=db, current_user=admin))
    db.refresh(cash)
    # Undo +400 absolute jump from 100→500, keep later -50 → 50
    assert cash.balance == 50


def test_sales_confirm_and_revert_update_partner_balance(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    partner = add_partner(db, balance=0)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    db.commit()

    order = Order(
        number="SALE-1",
        type="sale",
        partner_id=partner.id,
        warehouse_id=warehouse.id,
        user_id=user.id,
        status="draft",
        subtotal=200,
        total=200,
    )
    db.add(order)
    db.commit()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=2,
            price=100,
            total=200,
        )
    )
    db.commit()

    run(main.sales_confirm(order.id, db=db, current_user=user))
    db.refresh(partner)
    db.refresh(order)
    assert order.status == "completed"
    assert partner.balance == 200

    run(main.sales_revert(order.id, db=db, current_user=user))
    db.refresh(partner)
    db.refresh(order)
    assert order.status == "draft"
    assert partner.balance == 0
