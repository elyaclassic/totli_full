import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Base,
    Product,
    Production,
    Recipe,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    Warehouse,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def seed_product_and_warehouse(db):
    warehouse = Warehouse(code="WH", name="Warehouse", is_active=True)
    product = Product(code="P1", name="Product", type="tayyor", purchase_price=10)
    db.add_all([warehouse, product])
    db.commit()
    return warehouse, product


def test_stock_adjustment_confirmation_sets_absolute_quantity_without_double_apply(db):
    from main import qoldiqlar_tovar_hujjat_tasdiqlash

    warehouse, product = seed_product_and_warehouse(db)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=5))
    doc = StockAdjustmentDoc(number="QLD-1", status="draft", user_id=1)
    db.add(doc)
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=10,
        )
    )
    db.commit()

    response = asyncio.run(
        qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=SimpleNamespace(id=1))
    )

    stock_rows = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).all()
    movement = db.query(StockMovement).one()
    assert response.status_code == 303
    assert len(stock_rows) == 1
    assert stock_rows[0].quantity == 10
    assert movement.quantity_change == 5
    assert movement.quantity_after == 10
    assert db.query(StockAdjustmentDoc).get(doc.id).status == "confirmed"


def test_stock_adjustment_confirmation_creates_one_stock_row_for_new_item(db):
    from main import qoldiqlar_tovar_hujjat_tasdiqlash

    warehouse, product = seed_product_and_warehouse(db)
    doc = StockAdjustmentDoc(number="QLD-2", status="draft", user_id=1)
    db.add(doc)
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=7,
        )
    )
    db.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=SimpleNamespace(id=1)))

    stock_rows = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).all()
    movement = db.query(StockMovement).one()
    assert len(stock_rows) == 1
    assert stock_rows[0].quantity == 7
    assert movement.stock_id == stock_rows[0].id
    assert movement.quantity_change == 7
    assert movement.quantity_after == 7


def test_production_completion_adds_output_once(db):
    from main import _do_complete_production_stock

    source_warehouse = Warehouse(code="SRC", name="Source", is_active=True)
    output_warehouse = Warehouse(code="OUT", name="Output", is_active=True)
    output_product = Product(code="OUT", name="Output product", type="tayyor", purchase_price=10)
    recipe = Recipe(product=output_product, name="Recipe", output_quantity=3)
    db.add_all([source_warehouse, output_warehouse, output_product, recipe])
    db.commit()
    db.add(Stock(warehouse_id=output_warehouse.id, product_id=output_product.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=source_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=2,
        user_id=1,
    )
    db.add(production)
    db.commit()

    result = _do_complete_production_stock(db, production, recipe)
    db.flush()

    stock_rows = db.query(Stock).filter_by(
        warehouse_id=output_warehouse.id,
        product_id=output_product.id,
    ).all()
    movement = db.query(StockMovement).one()
    assert result is None
    assert len(stock_rows) == 1
    assert stock_rows[0].quantity == 8
    assert movement.quantity_change == 6
    assert movement.quantity_after == 8
