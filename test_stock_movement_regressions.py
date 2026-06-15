import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _user(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin")
    db.add(user)
    db.flush()
    return user


def _warehouse(db, code="WH"):
    warehouse = Warehouse(code=code, name=code)
    db.add(warehouse)
    db.flush()
    return warehouse


def _product(db, code, name=None):
    product = Product(code=code, name=name or code, type="product")
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirm_applies_delta_once(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session, "P1")
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
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

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    movement = db_session.query(StockMovement).one()
    assert stock.quantity == 150
    assert doc.status == "confirmed"
    assert movement.quantity_change == 50
    assert movement.quantity_after == 150


def test_stock_adjustment_revert_uses_recorded_movement_delta(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session, "P1")
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
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
    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    revert = (
        db_session.query(StockMovement)
        .filter(StockMovement.operation_type == "adjustment_revert")
        .one()
    )
    assert stock.quantity == 100
    assert doc.status == "draft"
    assert revert.quantity_change == -50
    assert revert.quantity_after == 100


def test_stock_adjustment_revert_repairs_legacy_double_applied_movement(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session, "P1")
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=200)
    doc = StockAdjustmentDoc(number="QLD-legacy", user_id=user.id, status="confirmed")
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
    db_session.add(
        StockMovement(
            stock_id=stock.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            operation_type="adjustment",
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            document_number=doc.number,
            quantity_change=50,
            quantity_after=200,
            user_id=user.id,
        )
    )
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    db_session.refresh(stock)
    revert = (
        db_session.query(StockMovement)
        .filter(StockMovement.operation_type == "adjustment_revert")
        .one()
    )
    assert stock.quantity == 100
    assert revert.quantity_change == -100


def test_production_completion_adds_finished_goods_once(db_session):
    user = _user(db_session)
    input_warehouse = _warehouse(db_session, "RAW")
    output_warehouse = _warehouse(db_session, "OUT")
    raw = _product(db_session, "RAW-P", "Raw")
    finished = _product(db_session, "FIN-P", "Finished")
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=2)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=1))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=input_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=3,
        status="draft",
        user_id=user.id,
    )
    db_session.add_all([
        Stock(warehouse_id=input_warehouse.id, product_id=raw.id, quantity=10),
        Stock(warehouse_id=output_warehouse.id, product_id=finished.id, quantity=5),
        production,
    ])
    db_session.commit()

    err = main._do_complete_production_stock(db_session, production, recipe)
    db_session.commit()

    raw_stock = db_session.query(Stock).filter_by(
        warehouse_id=input_warehouse.id,
        product_id=raw.id,
    ).one()
    finished_stock = db_session.query(Stock).filter_by(
        warehouse_id=output_warehouse.id,
        product_id=finished.id,
    ).one()
    output_movement = (
        db_session.query(StockMovement)
        .filter(StockMovement.operation_type == "production_output")
        .one()
    )
    assert err is None
    assert raw_stock.quantity == 7
    assert finished_stock.quantity == 11
    assert output_movement.quantity_change == 6
    assert output_movement.quantity_after == 11


def test_complete_production_is_idempotent_once_completed(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    raw = _product(db_session, "RAW-P", "Raw")
    finished = _product(db_session, "FIN-P", "Finished")
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=1))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=2,
        status="draft",
        user_id=user.id,
    )
    db_session.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw.id, quantity=10),
        production,
    ])
    db_session.commit()

    asyncio.run(main.complete_production(production.id, db_session, user))
    asyncio.run(main.complete_production(production.id, db_session, user))

    raw_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=raw.id,
    ).one()
    finished_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=finished.id,
    ).one()
    assert raw_stock.quantity == 8
    assert finished_stock.quantity == 2
    assert db_session.query(StockMovement).count() == 2


def test_completed_production_delete_is_blocked(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    finished = _product(db_session, "FIN-P", "Finished")
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1)
    db_session.add(recipe)
    db_session.flush()
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=1,
        status="completed",
        user_id=user.id,
    )
    db_session.add(production)
    db_session.commit()

    response = asyncio.run(main.delete_production(production.id, db_session, user))

    assert response.status_code == 303
    assert "error=delete" in response.headers["location"]
    assert db_session.query(Production).filter_by(id=production.id).one()
