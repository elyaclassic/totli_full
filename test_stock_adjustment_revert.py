"""Regression: stock-count confirm is absolute; revert must invert applied delta, not subtract counted qty."""
import asyncio
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import (
    Base,
    Product,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    User,
    Warehouse,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def run(coro):
    return asyncio.run(coro)


def _seed(db, qty=100.0):
    user = User(
        username="admin",
        password_hash="x",
        full_name="Admin",
        role="admin",
        is_active=True,
    )
    wh = Warehouse(code="WH1", name="Asosiy ombor", is_active=True)
    product = Product(
        code="P100",
        name="Yong'oq",
        type="hom_ashyo",
        is_active=True,
        sale_price=5000,
        purchase_price=3000,
    )
    db.add_all([user, wh, product])
    db.flush()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=qty)
    db.add(stock)
    db.commit()
    return user, wh, product, stock


def _draft_doc(db, user, wh, product, counted_qty):
    doc = StockAdjustmentDoc(
        number=f"QLD-TEST-{datetime.now().strftime('%H%M%S%f')}",
        date=datetime.now(),
        user_id=user.id,
        status="draft",
    )
    db.add(doc)
    db.flush()
    db.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        product_id=product.id,
        warehouse_id=wh.id,
        quantity=counted_qty,
        cost_price=0,
        sale_price=0,
    ))
    db.commit()
    db.refresh(doc)
    return doc


def test_matching_count_confirm_then_revert_does_not_wipe(db):
    """Counted qty equals on-hand: revert used to subtract that qty and zero stock."""
    from main import qoldiqlar_tovar_hujjat_revert, qoldiqlar_tovar_hujjat_tasdiqlash

    user, wh, product, stock = _seed(db, qty=100)
    doc = _draft_doc(db, user, wh, product, counted_qty=100)

    resp = run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))
    assert resp.status_code == 303
    db.refresh(stock)
    db.refresh(doc)
    assert doc.status == "confirmed"
    assert stock.quantity == 100

    resp = run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))
    assert resp.status_code == 303
    db.refresh(stock)
    db.refresh(doc)
    assert doc.status == "draft"
    assert stock.quantity == 100


def test_changed_count_confirm_then_revert_restores_previous(db):
    from main import qoldiqlar_tovar_hujjat_revert, qoldiqlar_tovar_hujjat_tasdiqlash

    user, wh, product, stock = _seed(db, qty=100)
    doc = _draft_doc(db, user, wh, product, counted_qty=80)

    resp = run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))
    assert resp.status_code == 303
    db.refresh(stock)
    assert stock.quantity == 80

    resp = run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))
    assert resp.status_code == 303
    db.refresh(stock)
    assert stock.quantity == 100


def test_revert_preserves_later_independent_stock_change(db):
    """After confirm, a later sale/transfer must survive revert (delta invert, not absolute restore)."""
    from main import qoldiqlar_tovar_hujjat_revert, qoldiqlar_tovar_hujjat_tasdiqlash

    user, wh, product, stock = _seed(db, qty=100)
    doc = _draft_doc(db, user, wh, product, counted_qty=80)

    run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))
    db.refresh(stock)
    assert stock.quantity == 80

    stock.quantity = 70  # later independent issue of 10
    db.commit()

    run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))
    db.refresh(stock)
    assert stock.quantity == 90


def test_import_style_confirmed_doc_revert_restores_previous(db):
    """Warehouse Excel auto-confirm writes absolute qty + a matching StockMovement (no double-apply)."""
    from main import qoldiqlar_tovar_hujjat_revert

    user, wh, product, stock = _seed(db, qty=50)
    doc = StockAdjustmentDoc(
        number="QLD-IMPORT-1",
        date=datetime.now(),
        user_id=user.id,
        status="confirmed",
    )
    db.add(doc)
    db.flush()
    db.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        product_id=product.id,
        warehouse_id=wh.id,
        quantity=80,
        cost_price=0,
        sale_price=0,
    ))
    stock.quantity = 80
    db.add(StockMovement(
        stock_id=stock.id,
        warehouse_id=wh.id,
        product_id=product.id,
        operation_type="adjustment",
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        document_number=doc.number,
        quantity_change=30,
        quantity_after=80,
        user_id=user.id,
        note="Exceldan yuklash",
    ))
    db.commit()

    resp = run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))
    assert resp.status_code == 303
    db.refresh(stock)
    db.refresh(doc)
    assert doc.status == "draft"
    assert stock.quantity == 50
