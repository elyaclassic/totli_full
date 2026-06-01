import asyncio

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
    User,
    Warehouse,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_stock_adjustment_confirm_and_revert_apply_delta_once(db):
    user = User(username="admin", password_hash="x", role="admin", is_active=True)
    warehouse = Warehouse(code="W1", name="Main")
    product = Product(code="P1", name="Product", type="product")
    db.add_all([user, warehouse, product])
    db.flush()
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
    db.add(doc)
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
        )
    )
    db.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 50
    movement = db.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert movement.quantity_change == 40
    assert movement.quantity_after == 50

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))

    db.refresh(stock)
    assert stock.quantity == 10
    revert_movement = db.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert_movement.quantity_change == -40
    assert revert_movement.quantity_after == 10


def test_production_completion_adds_output_once(db):
    warehouse = Warehouse(code="W1", name="Main")
    raw_product = Product(code="RAW", name="Raw", type="material", purchase_price=5)
    output_product = Product(code="OUT", name="Output", type="product", purchase_price=10)
    db.add_all([warehouse, raw_product, output_product])
    db.flush()
    db.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw_product.id, quantity=100),
        Stock(warehouse_id=warehouse.id, product_id=output_product.id, quantity=5),
    ])
    recipe = Recipe(product_id=output_product.id, name="Recipe", output_quantity=2)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=3,
        status="draft",
    )
    db.add(production)
    db.commit()

    error_response = main._do_complete_production_stock(db, production, recipe)
    assert error_response is None
    db.commit()

    raw_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw_product.id).one()
    output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output_product.id).one()
    assert raw_stock.quantity == 94
    assert output_stock.quantity == 11
    output_movement = db.query(StockMovement).filter_by(operation_type="production_output").one()
    assert output_movement.quantity_change == 6
    assert output_movement.quantity_after == 11


def test_completed_production_submit_is_idempotent(db):
    user = User(username="admin", password_hash="x", role="admin", is_active=True)
    warehouse = Warehouse(code="W1", name="Main")
    raw_product = Product(code="RAW", name="Raw", type="material", purchase_price=5)
    output_product = Product(code="OUT", name="Output", type="product", purchase_price=10)
    db.add_all([user, warehouse, raw_product, output_product])
    db.flush()
    db.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw_product.id, quantity=94),
        Stock(warehouse_id=warehouse.id, product_id=output_product.id, quantity=11),
    ])
    recipe = Recipe(product_id=output_product.id, name="Recipe", output_quantity=2)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=2))
    production = Production(
        number="PR-2",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=3,
        status="completed",
        user_id=user.id,
    )
    db.add(production)
    db.commit()

    asyncio.run(main.complete_production(production.id, db=db, current_user=user))

    raw_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw_product.id).one()
    output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output_product.id).one()
    assert raw_stock.quantity == 94
    assert output_stock.quantity == 11
    assert db.query(StockMovement).count() == 0
