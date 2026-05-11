import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main as app_main
from app.models.database import (
    Base,
    Production,
    Product,
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
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def _admin_user(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    db.add(user)
    db.flush()
    return user


def _warehouse(db, code="WH"):
    warehouse = Warehouse(code=code, name=code, is_active=True)
    db.add(warehouse)
    db.flush()
    return warehouse


def _product(db, code, name=None, product_type="product"):
    product = Product(code=code, name=name or code, type=product_type, is_active=True)
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirm_and_revert_apply_one_delta(db_session):
    user = _admin_user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session, "P1")
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=10,
        )
    )
    db_session.commit()

    asyncio.run(app_main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user))
    db_session.refresh(stock)
    db_session.refresh(doc)

    assert doc.status == "confirmed"
    assert stock.quantity == 10
    movements = db_session.query(StockMovement).filter_by(document_id=doc.id).order_by(StockMovement.id).all()
    assert [(m.quantity_change, m.quantity_after) for m in movements] == [(-90, 10)]

    asyncio.run(app_main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))
    db_session.refresh(stock)
    db_session.refresh(doc)

    assert doc.status == "draft"
    assert stock.quantity == 100
    movements = db_session.query(StockMovement).filter_by(document_id=doc.id).order_by(StockMovement.id).all()
    assert [(m.operation_type, m.quantity_change, m.quantity_after) for m in movements] == [
        ("adjustment", -90, 10),
        ("adjustment_revert", 90, 100),
    ]

    asyncio.run(app_main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user))
    asyncio.run(app_main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))
    db_session.refresh(stock)

    assert stock.quantity == 100


def test_production_completion_adds_finished_goods_once(db_session):
    user = _admin_user(db_session)
    warehouse = _warehouse(db_session)
    material = _product(db_session, "M1", product_type="material")
    output = _product(db_session, "FG1")
    recipe = Recipe(product_id=output.id, name="FG recipe", output_quantity=3)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=4,
        status="draft",
        user_id=user.id,
    )
    db_session.add_all(
        [
            production,
            Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=20),
            Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=5),
        ]
    )
    db_session.commit()

    error_response = app_main._do_complete_production_stock(db_session, production, recipe)
    db_session.flush()

    assert error_response is None
    material_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
    output_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
    assert material_stock.quantity == 12
    assert output_stock.quantity == 17


def test_complete_production_does_not_reapply_completed_order(db_session):
    user = _admin_user(db_session)
    warehouse = _warehouse(db_session)
    material = _product(db_session, "M1", product_type="material")
    output = _product(db_session, "FG1")
    recipe = Recipe(product_id=output.id, name="FG recipe", output_quantity=1)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PR-2",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=4,
        status="completed",
        user_id=user.id,
    )
    material_stock = Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=20)
    output_stock = Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=5)
    db_session.add_all([production, material_stock, output_stock])
    db_session.commit()

    asyncio.run(app_main.complete_production(production.id, db=db_session, current_user=user))
    db_session.refresh(material_stock)
    db_session.refresh(output_stock)

    assert material_stock.quantity == 20
    assert output_stock.quantity == 5
    assert db_session.query(StockMovement).count() == 0
