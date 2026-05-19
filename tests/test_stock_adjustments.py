import asyncio

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
from main import (
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seed_adjustment_doc(db, target_quantity, starting_quantity=None):
    user = User(username="admin", full_name="Admin", role="admin", is_active=True)
    warehouse = Warehouse(code="W1", name="Main warehouse", is_active=True)
    product = Product(code="P1", name="Product", type="tayyor", is_active=True)
    db.add_all([user, warehouse, product])
    db.flush()

    if starting_quantity is not None:
        db.add(
            Stock(
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=starting_quantity,
            )
        )

    doc = StockAdjustmentDoc(number="QLD-TEST-0001", user_id=user.id, status="draft")
    db.add(doc)
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=target_quantity,
        )
    )
    db.commit()
    return user, warehouse, product, doc


def test_stock_adjustment_sets_existing_stock_to_target_quantity(db_session):
    user, warehouse, product, doc = _seed_adjustment_doc(
        db_session,
        target_quantity=20,
        starting_quantity=10,
    )

    response = asyncio.run(
        qoldiqlar_tovar_hujjat_tasdiqlash(
            doc.id,
            db=db_session,
            current_user=user,
        )
    )

    assert response.status_code == 303
    stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=product.id,
    ).one()
    assert stock.quantity == pytest.approx(20)

    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == pytest.approx(10)
    assert movement.quantity_after == pytest.approx(20)


def test_stock_adjustment_creates_one_stock_row_for_new_stock(db_session):
    user, warehouse, product, doc = _seed_adjustment_doc(
        db_session,
        target_quantity=7,
        starting_quantity=None,
    )

    asyncio.run(
        qoldiqlar_tovar_hujjat_tasdiqlash(
            doc.id,
            db=db_session,
            current_user=user,
        )
    )

    stocks = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=product.id,
    ).all()
    assert len(stocks) == 1
    assert stocks[0].quantity == pytest.approx(7)


def test_stock_adjustment_revert_restores_previous_quantity(db_session):
    user, warehouse, product, doc = _seed_adjustment_doc(
        db_session,
        target_quantity=20,
        starting_quantity=10,
    )
    asyncio.run(
        qoldiqlar_tovar_hujjat_tasdiqlash(
            doc.id,
            db=db_session,
            current_user=user,
        )
    )

    response = asyncio.run(
        qoldiqlar_tovar_hujjat_revert(
            doc.id,
            db=db_session,
            current_user=user,
        )
    )

    assert response.status_code == 303
    stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=product.id,
    ).one()
    assert stock.quantity == pytest.approx(10)

    revert_movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert revert_movement.quantity_change == pytest.approx(-10)
    assert revert_movement.quantity_after == pytest.approx(10)
