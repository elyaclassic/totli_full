import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
    Product,
    Production,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    Warehouse,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _warehouse(db, code="WH", name="Warehouse"):
    warehouse = Warehouse(code=code, name=name, is_active=True)
    db.add(warehouse)
    db.flush()
    return warehouse


def _product(db, code="P", name="Product", product_type="product", purchase_price=0):
    product = Product(
        code=code,
        name=name,
        type=product_type,
        purchase_price=purchase_price,
        is_active=True,
    )
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirmation_sets_absolute_quantity_once(db_session):
    warehouse = _warehouse(db_session)
    product = _product(db_session)
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    doc = StockAdjustmentDoc(number="QLD-TEST", status="draft")
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=140,
        )
    )
    db_session.commit()

    asyncio.run(
        main.qoldiqlar_tovar_hujjat_tasdiqlash(
            doc.id,
            db_session,
            SimpleNamespace(id=42),
        )
    )

    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    movement = db_session.query(StockMovement).filter_by(document_type="StockAdjustmentDoc", document_id=doc.id).one()

    assert stock.quantity == 140
    assert movement.quantity_change == 40
    assert movement.quantity_after == 140


def test_production_completion_adds_finished_goods_once(db_session):
    input_warehouse = _warehouse(db_session, code="RAW", name="Raw")
    output_warehouse = _warehouse(db_session, code="FIN", name="Finished")
    material = _product(db_session, code="MAT", name="Material", product_type="material", purchase_price=5)
    finished = _product(db_session, code="FINISHED", name="Finished good", purchase_price=10)

    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=3)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=5))
    production = Production(
        number="PR-TEST",
        recipe_id=recipe.id,
        warehouse_id=input_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=2,
        user_id=42,
    )
    db_session.add_all(
        [
            production,
            Stock(warehouse_id=input_warehouse.id, product_id=material.id, quantity=50),
            Stock(warehouse_id=output_warehouse.id, product_id=finished.id, quantity=10),
        ]
    )
    db_session.commit()

    result = main._do_complete_production_stock(db_session, production, recipe)
    db_session.commit()

    assert result is None
    material_stock = db_session.query(Stock).filter_by(warehouse_id=input_warehouse.id, product_id=material.id).one()
    finished_stock = db_session.query(Stock).filter_by(warehouse_id=output_warehouse.id, product_id=finished.id).one()
    output_movement = (
        db_session.query(StockMovement)
        .filter_by(document_type="Production", document_id=production.id, operation_type="production_output")
        .one()
    )

    assert material_stock.quantity == 40
    assert finished_stock.quantity == 16
    assert output_movement.quantity_change == 6
    assert output_movement.quantity_after == 16
