import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Base,
    Product,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    User,
    Warehouse,
    Production,
)
from main import (
    _do_complete_production_stock,
    create_stock_movement,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def stock_quantity(db, warehouse_id, product_id):
    return db.query(Stock).filter(
        Stock.warehouse_id == warehouse_id,
        Stock.product_id == product_id,
    ).one().quantity


def test_stock_adjustment_confirm_sets_target_once_and_revert_reverses_delta(db_session):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin")
    warehouse = Warehouse(code="W1", name="Main warehouse")
    product = Product(code="P1", name="Halva", type="product")
    db_session.add_all([user, warehouse, product])
    db_session.flush()

    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.flush()
    item = StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=50,
    )
    db_session.add(item)
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user))

    assert stock_quantity(db_session, warehouse.id, product.id) == pytest.approx(50)
    db_session.refresh(item)
    assert item.previous_quantity == pytest.approx(100)

    adjustment = db_session.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert adjustment.quantity_change == pytest.approx(-50)
    assert adjustment.quantity_after == pytest.approx(50)

    create_stock_movement(
        db=db_session,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity_change=-5,
        operation_type="sale",
        document_type="Sale",
        document_id=1,
        document_number="SALE-1",
        user_id=user.id,
    )
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))

    assert stock_quantity(db_session, warehouse.id, product.id) == pytest.approx(95)
    revert = db_session.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert.quantity_change == pytest.approx(50)
    assert revert.quantity_after == pytest.approx(95)


def test_production_completion_adds_finished_goods_once(db_session):
    user = User(username="operator", password_hash="x", full_name="Operator", role="user")
    warehouse = Warehouse(code="W1", name="Main warehouse")
    raw_product = Product(code="RAW", name="Sugar", type="material", purchase_price=2)
    finished_product = Product(code="FIN", name="Finished halva", type="product", purchase_price=10)
    db_session.add_all([user, warehouse, raw_product, finished_product])
    db_session.flush()

    recipe = Recipe(product_id=finished_product.id, name="Halva recipe", output_quantity=2)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=3))

    production = Production(
        number="PROD-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=4,
        user_id=user.id,
        status="in_progress",
    )
    db_session.add(production)
    db_session.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw_product.id, quantity=20),
        Stock(warehouse_id=warehouse.id, product_id=finished_product.id, quantity=7),
    ])
    db_session.commit()

    result = _do_complete_production_stock(db_session, production, recipe)

    assert result is None
    assert stock_quantity(db_session, warehouse.id, raw_product.id) == pytest.approx(8)
    assert stock_quantity(db_session, warehouse.id, finished_product.id) == pytest.approx(15)

    output_movement = db_session.query(StockMovement).filter_by(operation_type="production_output").one()
    assert output_movement.quantity_change == pytest.approx(8)
    assert output_movement.quantity_after == pytest.approx(15)
