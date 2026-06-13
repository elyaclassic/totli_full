import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
    Product,
    Recipe,
    RecipeItem,
    Production,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    User,
    Warehouse,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def make_user(db, role="admin"):
    user = User(username=f"{role}-user", full_name="Test User", role=role, is_active=True)
    db.add(user)
    db.flush()
    return user


def make_warehouse(db, code="WH"):
    warehouse = Warehouse(code=code, name=code, is_active=True)
    db.add(warehouse)
    db.flush()
    return warehouse


def make_product(db, code="P", name="Product"):
    product = Product(code=code, name=name, type="product", is_active=True)
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirm_and_revert_use_delta_once(db_session):
    user = make_user(db_session)
    warehouse = make_warehouse(db_session)
    product = make_product(db_session)
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="ADJ-1", status="draft", user_id=user.id)
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=30,
        )
    )
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    assert stock.quantity == 30
    assert doc.status == "confirmed"
    movement = db_session.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert movement.quantity_change == -70
    assert movement.quantity_after == 30

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    assert stock.quantity == 100
    assert doc.status == "draft"
    revert_movement = db_session.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert_movement.quantity_change == 70
    assert revert_movement.quantity_after == 100


def test_production_completion_applies_output_once_and_is_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda db: None)
    user = make_user(db_session)
    raw_warehouse = make_warehouse(db_session, "RAW")
    output_warehouse = make_warehouse(db_session, "OUT")
    raw_product = make_product(db_session, "RAW-MAT", "Raw material")
    output_product = make_product(db_session, "FIN", "Finished product")
    recipe = Recipe(product_id=output_product.id, name="Recipe", output_quantity=2)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=3))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=raw_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=5,
        status="draft",
        user_id=user.id,
    )
    db_session.add_all(
        [
            Stock(warehouse_id=raw_warehouse.id, product_id=raw_product.id, quantity=100),
            Stock(warehouse_id=output_warehouse.id, product_id=output_product.id, quantity=10),
            production,
        ]
    )
    db_session.commit()

    asyncio.run(main.complete_production(production.id, db_session, user))

    raw_stock = db_session.query(Stock).filter_by(
        warehouse_id=raw_warehouse.id,
        product_id=raw_product.id,
    ).one()
    output_stock = db_session.query(Stock).filter_by(
        warehouse_id=output_warehouse.id,
        product_id=output_product.id,
    ).one()
    assert raw_stock.quantity == 85
    assert output_stock.quantity == 20
    assert db_session.query(StockMovement).filter_by(operation_type="production_output").count() == 1

    asyncio.run(main.complete_production(production.id, db_session, user))

    db_session.refresh(raw_stock)
    db_session.refresh(output_stock)
    assert raw_stock.quantity == 85
    assert output_stock.quantity == 20
    assert db_session.query(StockMovement).filter_by(operation_type="production_output").count() == 1
