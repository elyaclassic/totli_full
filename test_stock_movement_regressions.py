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
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _add_user(db_session):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin")
    db_session.add(user)
    db_session.flush()
    return user


def _add_warehouse(db_session):
    warehouse = Warehouse(code="WH", name="Warehouse")
    db_session.add(warehouse)
    db_session.flush()
    return warehouse


def _add_product(db_session, code, name, product_type="product", purchase_price=0):
    product = Product(
        code=code,
        name=name,
        type=product_type,
        purchase_price=purchase_price,
    )
    db_session.add(product)
    db_session.flush()
    return product


def test_stock_adjustment_confirm_sets_absolute_quantity_and_reverts_delta(db_session):
    user = _add_user(db_session)
    warehouse = _add_warehouse(db_session)
    product = _add_product(db_session, "P1", "Product")
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="QLD-1", status="draft", user_id=user.id)
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
        )
    )
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    db_session.refresh(stock)
    assert stock.quantity == 50
    movement = db_session.query(StockMovement).one()
    assert movement.quantity_change == 40
    assert movement.quantity_after == 50

    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    assert stock.quantity == 10
    assert doc.status == "draft"


def test_stock_adjustment_confirm_creates_one_stock_row_for_new_balance(db_session):
    user = _add_user(db_session)
    warehouse = _add_warehouse(db_session)
    product = _add_product(db_session, "P1", "Product")
    doc = StockAdjustmentDoc(number="QLD-1", status="draft", user_id=user.id)
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
        )
    )
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    stocks = db_session.query(Stock).all()
    assert len(stocks) == 1
    assert stocks[0].quantity == 50
    movement = db_session.query(StockMovement).one()
    assert movement.quantity_change == 50
    assert movement.quantity_after == 50


def test_production_completion_adds_finished_goods_once(db_session):
    user = _add_user(db_session)
    warehouse = _add_warehouse(db_session)
    material = _add_product(db_session, "M1", "Material", product_type="material", purchase_price=3)
    output = _add_product(db_session, "P1", "Finished", purchase_price=10)
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=1)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=5,
        status="draft",
        user_id=user.id,
    )
    db_session.add_all([
        Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=100),
        Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=20),
        production,
    ])
    db_session.commit()

    error_response = _do_complete_production_stock(db_session, production, recipe)

    assert error_response is None
    material_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=material.id,
    ).one()
    output_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=output.id,
    ).one()
    assert material_stock.quantity == 90
    assert output_stock.quantity == 25
    output_movement = db_session.query(StockMovement).filter_by(
        operation_type="production_output",
    ).one()
    assert output_movement.quantity_change == 5
    assert output_movement.quantity_after == 25
