import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Base,
    Product,
    Production,
    ProductionItem,
    Recipe,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    User,
    Warehouse,
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
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _user(db_session, role="admin"):
    user = User(username=f"{role}_user", password_hash="x", full_name="Test User", role=role, is_active=True)
    db_session.add(user)
    db_session.flush()
    return user


def _warehouse(db_session, code):
    warehouse = Warehouse(code=code, name=code, is_active=True)
    db_session.add(warehouse)
    db_session.flush()
    return warehouse


def _product(db_session, code, name=None, purchase_price=0):
    product = Product(code=code, name=name or code, type="product", purchase_price=purchase_price, is_active=True)
    db_session.add(product)
    db_session.flush()
    return product


def test_stock_adjustment_confirm_sets_target_quantity_once(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session, "WH")
    product = _product(db_session, "P")
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    doc = StockAdjustmentDoc(number="QLD-1", status="draft", user_id=user.id)
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=80,
        )
    )
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    movement = db_session.query(StockMovement).filter_by(document_id=doc.id, operation_type="adjustment").one()
    assert stock.quantity == 80
    assert movement.quantity_change == -20
    assert movement.quantity_after == 80
    assert doc.status == "confirmed"


def test_stock_adjustment_revert_reverses_recorded_delta(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session, "WH")
    product = _product(db_session, "P")
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    doc = StockAdjustmentDoc(number="QLD-2", status="draft", user_id=user.id)
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=80,
        )
    )
    db_session.commit()
    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    create_stock_movement(
        db=db_session,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity_change=5,
        operation_type="purchase",
        document_type="Purchase",
        document_id=123,
    )
    db_session.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    revert_movement = db_session.query(StockMovement).filter_by(
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert stock.quantity == 105
    assert revert_movement.quantity_change == 20
    assert revert_movement.quantity_after == 105
    assert doc.status == "draft"


def test_production_completion_records_output_once(db_session):
    user = _user(db_session, role="user")
    raw_warehouse = _warehouse(db_session, "RAW")
    output_warehouse = _warehouse(db_session, "OUT")
    material = _product(db_session, "MAT", purchase_price=2)
    finished = _product(db_session, "FIN", purchase_price=5)
    db_session.add_all([
        Stock(warehouse_id=raw_warehouse.id, product_id=material.id, quantity=20),
        Stock(warehouse_id=output_warehouse.id, product_id=finished.id, quantity=50),
    ])
    recipe = Recipe(product_id=finished.id, name="Finished recipe", output_quantity=1, is_active=True)
    db_session.add(recipe)
    db_session.flush()
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=raw_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=10,
        status="draft",
        user_id=user.id,
    )
    db_session.add(production)
    db_session.flush()
    db_session.add(ProductionItem(production_id=production.id, product_id=material.id, quantity=4))
    db_session.commit()
    db_session.refresh(production)
    db_session.refresh(recipe)

    result = _do_complete_production_stock(db_session, production, recipe)
    db_session.flush()

    assert result is None
    raw_stock = db_session.query(Stock).filter_by(warehouse_id=raw_warehouse.id, product_id=material.id).one()
    output_stock = db_session.query(Stock).filter_by(warehouse_id=output_warehouse.id, product_id=finished.id).one()
    output_movement = db_session.query(StockMovement).filter_by(
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert raw_stock.quantity == 16
    assert output_stock.quantity == 60
    assert output_movement.quantity_change == 10
    assert output_movement.quantity_after == 60
