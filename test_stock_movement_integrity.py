import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    User,
    Warehouse,
)
from main import (
    _do_complete_production_stock,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _base_entities(db):
    user = User(username="admin", password_hash="hash", full_name="Admin", role="admin")
    warehouse = Warehouse(code="WH", name="Main")
    product = Product(code="P1", name="Product", type="product", purchase_price=10)
    db.add_all([user, warehouse, product])
    db.flush()
    return user, warehouse, product


def test_stock_adjustment_confirm_sets_target_once_and_revert_uses_delta(db_session):
    user, warehouse, product = _base_entities(db_session)
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=150,
        )
    )
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    adjusted_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=product.id,
    ).one()
    assert adjusted_stock.quantity == 150

    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 50
    assert movement.quantity_after == 150

    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    reverted_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=product.id,
    ).one()
    assert reverted_stock.quantity == 100

    revert_movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert revert_movement.quantity_change == -50
    assert revert_movement.quantity_after == 100
    assert doc.status == "draft"


def test_stock_adjustment_confirm_creates_one_stock_row_for_new_product(db_session):
    user, warehouse, product = _base_entities(db_session)
    doc = StockAdjustmentDoc(number="ADJ-NEW", user_id=user.id, status="draft")
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=25,
        )
    )
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    stocks = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=product.id,
    ).all()
    assert len(stocks) == 1
    assert stocks[0].quantity == 25

    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 25
    assert movement.quantity_after == 25


def test_production_completion_adds_finished_goods_once(db_session):
    user = User(username="maker", password_hash="hash", full_name="Maker", role="manager")
    warehouse = Warehouse(code="WH", name="Main")
    material = Product(code="M1", name="Material", type="material", purchase_price=4)
    finished = Product(code="F1", name="Finished", type="product", purchase_price=10)
    db_session.add_all([user, warehouse, material, finished])
    db_session.flush()

    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=2)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=3))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=5,
        user_id=user.id,
        status="in_progress",
    )
    db_session.add_all([
        production,
        Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=100),
        Stock(warehouse_id=warehouse.id, product_id=finished.id, quantity=7),
    ])
    db_session.commit()

    result = _do_complete_production_stock(db_session, production, recipe)
    db_session.flush()

    assert result is None
    material_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=material.id,
    ).one()
    finished_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=finished.id,
    ).one()
    assert material_stock.quantity == 85
    assert finished_stock.quantity == 17

    output_movement = db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert output_movement.quantity_change == 10
    assert output_movement.quantity_after == 17
