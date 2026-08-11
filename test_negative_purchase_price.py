"""Regression: negative purchase line prices corrupt supplier AP and product cost."""
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
    PurchaseItem,
    Stock,
    User,
    Warehouse,
)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    db_file = tmp_path / "test_neg_price.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()

    def _get_db():
        try:
            yield session
        finally:
            pass

    monkeypatch.setattr(main, "SessionLocal", TestingSession)
    monkeypatch.setattr(main, "get_db", _get_db)
    yield session
    session.close()
    engine.dispose()


def _seed(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    partner = Partner(name="Supplier", code="S1", type="supplier", balance=0, is_active=True)
    wh = Warehouse(name="Main", code="W1", is_active=True)
    product = Product(name="Flour", code="F1", type="hom_ashyo", purchase_price=1000, sale_price=0, is_active=True)
    db.add_all([user, partner, wh, product])
    db.commit()
    db.refresh(user)
    db.refresh(partner)
    db.refresh(wh)
    db.refresh(product)
    return user, partner, wh, product


def test_purchase_add_item_rejects_negative_price(db_session):
    user, partner, wh, product = _seed(db_session)
    purchase = Purchase(
        number="P-TEST-1",
        partner_id=partner.id,
        warehouse_id=wh.id,
        total=0,
        status="draft",
        date=datetime.now(),
    )
    db_session.add(purchase)
    db_session.commit()
    db_session.refresh(purchase)

    result = asyncio.get_event_loop().run_until_complete(
        main.purchase_add_item(
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=10,
            price=-5000,
            db=db_session,
        )
    )
    assert isinstance(result, RedirectResponse)
    assert "error=item" in result.headers.get("location", "")
    assert db_session.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase.id).count() == 0
    db_session.refresh(purchase)
    assert (purchase.total or 0) == 0


def test_purchase_confirm_rejects_negative_price_line(db_session):
    user, partner, wh, product = _seed(db_session)
    purchase = Purchase(
        number="P-TEST-2",
        partner_id=partner.id,
        warehouse_id=wh.id,
        total=-50000,
        status="draft",
        date=datetime.now(),
    )
    db_session.add(purchase)
    db_session.flush()
    db_session.add(
        PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=10,
            price=-5000,
            total=-50000,
        )
    )
    db_session.commit()
    db_session.refresh(purchase)
    partner_balance_before = partner.balance
    product_cost_before = product.purchase_price

    with pytest.raises(Exception) as excinfo:
        asyncio.get_event_loop().run_until_complete(
            main.purchase_confirm(purchase_id=purchase.id, db=db_session, current_user=user)
        )
    assert excinfo.value.status_code == 400
    assert "manfiy" in str(excinfo.value.detail).lower()

    db_session.refresh(purchase)
    db_session.refresh(partner)
    db_session.refresh(product)
    assert purchase.status == "draft"
    assert partner.balance == partner_balance_before
    assert product.purchase_price == product_cost_before
    stock = (
        db_session.query(Stock)
        .filter(Stock.warehouse_id == wh.id, Stock.product_id == product.id)
        .first()
    )
    assert stock is None or (stock.quantity or 0) == 0


def test_purchase_add_item_allows_zero_price(db_session):
    user, partner, wh, product = _seed(db_session)
    purchase = Purchase(
        number="P-TEST-3",
        partner_id=partner.id,
        warehouse_id=wh.id,
        total=0,
        status="draft",
        date=datetime.now(),
    )
    db_session.add(purchase)
    db_session.commit()
    db_session.refresh(purchase)

    result = asyncio.get_event_loop().run_until_complete(
        main.purchase_add_item(
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=2,
            price=0,
            db=db_session,
        )
    )
    assert isinstance(result, RedirectResponse)
    assert "error=" not in (result.headers.get("location") or "")
    items = db_session.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase.id).all()
    assert len(items) == 1
    assert items[0].price == 0
