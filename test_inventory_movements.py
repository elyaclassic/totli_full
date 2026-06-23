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
    complete_production,
    delete_production,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


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


def _product(db, code="P", name="Product", purchase_price=0):
    product = Product(code=code, name=name, type="product", purchase_price=purchase_price)
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirm_sets_absolute_quantity_once(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session)
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=15,
    ))
    db_session.flush()

    response = asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user))

    assert response.status_code == 303
    db_session.refresh(stock)
    db_session.refresh(doc)
    assert stock.quantity == 15
    assert doc.status == "confirmed"
    movement = db_session.query(StockMovement).one()
    assert movement.operation_type == "adjustment"
    assert movement.quantity_change == 5
    assert movement.quantity_after == 15


def test_stock_adjustment_revert_applies_recorded_delta(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session)
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="QLD-2", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=15,
    ))
    db_session.flush()
    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user))

    response = asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))

    assert response.status_code == 303
    db_session.refresh(stock)
    db_session.refresh(doc)
    assert stock.quantity == 10
    assert doc.status == "draft"
    movements = db_session.query(StockMovement).order_by(StockMovement.id).all()
    assert [m.operation_type for m in movements] == ["adjustment", "adjustment_revert"]
    assert [m.quantity_change for m in movements] == [5, -5]
    assert movements[-1].quantity_after == 10


def test_production_completion_adds_finished_goods_once(db_session):
    user = _user(db_session)
    raw_warehouse = _warehouse(db_session, "RAW")
    output_warehouse = _warehouse(db_session, "OUT")
    raw_product = _product(db_session, "RAW-P", "Raw", purchase_price=2)
    finished_product = _product(db_session, "FIN-P", "Finished", purchase_price=5)
    recipe = Recipe(product_id=finished_product.id, name="Recipe", output_quantity=2)
    db_session.add(recipe)
    db_session.flush()
    recipe.items.append(RecipeItem(product_id=raw_product.id, quantity=3))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=raw_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=10,
        status="draft",
        user_id=user.id,
    )
    raw_stock = Stock(warehouse_id=raw_warehouse.id, product_id=raw_product.id, quantity=100)
    finished_stock = Stock(warehouse_id=output_warehouse.id, product_id=finished_product.id, quantity=50)
    db_session.add_all([production, raw_stock, finished_stock])
    db_session.flush()

    error_response = _do_complete_production_stock(db_session, production, recipe)

    assert error_response is None
    db_session.flush()
    db_session.refresh(raw_stock)
    db_session.refresh(finished_stock)
    assert raw_stock.quantity == 70
    assert finished_stock.quantity == 70
    output_movement = db_session.query(StockMovement).filter(
        StockMovement.operation_type == "production_output"
    ).one()
    assert output_movement.quantity_change == 20
    assert output_movement.quantity_after == 70


def test_completed_production_cannot_be_completed_again_or_deleted(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    raw_product = _product(db_session, "RAW-P", "Raw")
    finished_product = _product(db_session, "FIN-P", "Finished")
    recipe = Recipe(product_id=finished_product.id, name="Recipe", output_quantity=1)
    db_session.add(recipe)
    db_session.flush()
    recipe.items.append(RecipeItem(product_id=raw_product.id, quantity=1))
    production = Production(
        number="PR-2",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=5,
        status="completed",
        user_id=user.id,
    )
    stock = Stock(warehouse_id=warehouse.id, product_id=raw_product.id, quantity=25)
    db_session.add_all([production, stock])
    db_session.flush()

    complete_response = asyncio.run(complete_production(production.id, db=db_session, current_user=user))
    delete_response = asyncio.run(delete_production(production.id, db=db_session, current_user=user))

    assert complete_response.status_code == 303
    assert delete_response.status_code == 303
    db_session.refresh(stock)
    assert stock.quantity == 25
    assert db_session.query(StockMovement).count() == 0
    assert db_session.query(Production).filter(Production.id == production.id).one()
