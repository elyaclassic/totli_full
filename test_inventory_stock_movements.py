import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Base,
    Department,
    Employee,
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
    WarehouseTransfer,
    WarehouseTransferItem,
)
from main import (
    _do_complete_production_stock,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
    warehouse_transfer_confirm,
)


@pytest.fixture()
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
        engine.dispose()


def add_user(db, role="admin", username=None):
    user = User(
        username=username or f"{role}_user",
        password_hash="hash",
        full_name=f"{role.title()} User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def add_warehouse(db, code="WH", name="Warehouse"):
    warehouse = Warehouse(code=code, name=name, is_active=True)
    db.add(warehouse)
    db.flush()
    return warehouse


def add_department(db, code="DEPT", name="Department"):
    department = Department(code=code, name=name, is_active=True)
    db.add(department)
    db.flush()
    return department


def add_product(db, code="P1", name="Product", product_type="product", purchase_price=0):
    product = Product(
        code=code,
        name=name,
        type=product_type,
        purchase_price=purchase_price,
        sale_price=0,
        is_active=True,
    )
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirm_sets_target_quantity_once(db):
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="ADJ-001", user_id=user.id, status="draft")
    db.add(doc)
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
            cost_price=0,
            sale_price=0,
        )
    )
    db.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    movement = db.query(StockMovement).filter_by(document_id=doc.id, operation_type="adjustment").one()
    assert stock.quantity == 50
    assert movement.quantity_change == 40
    assert movement.quantity_after == 50
    assert doc.status == "confirmed"


def test_stock_adjustment_revert_restores_previous_quantity(db):
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    doc = StockAdjustmentDoc(number="ADJ-002", user_id=user.id, status="draft")
    db.add(doc)
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
            cost_price=0,
            sale_price=0,
        )
    )
    db.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))
    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    revert_movement = db.query(StockMovement).filter_by(
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert stock.quantity == 100
    assert revert_movement.quantity_change == 50
    assert revert_movement.quantity_after == 100
    assert doc.status == "draft"


def test_production_completion_adds_finished_goods_once(db):
    user = add_user(db)
    warehouse = add_warehouse(db)
    raw_material = add_product(db, code="M1", name="Raw", product_type="material", purchase_price=3)
    finished_product = add_product(db, code="F1", name="Finished", purchase_price=10)
    db.add(Stock(warehouse_id=warehouse.id, product_id=raw_material.id, quantity=100))
    db.add(Stock(warehouse_id=warehouse.id, product_id=finished_product.id, quantity=10))
    recipe = Recipe(product_id=finished_product.id, name="Recipe", output_quantity=1, is_active=True)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=raw_material.id, quantity=2))
    production = Production(
        number="PR-001",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=5,
        user_id=user.id,
        status="draft",
    )
    db.add(production)
    db.commit()

    error_response = _do_complete_production_stock(db, production, recipe)
    db.flush()

    assert error_response is None
    raw_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw_material.id).one()
    finished_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=finished_product.id).one()
    output_movement = db.query(StockMovement).filter_by(
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert raw_stock.quantity == 90
    assert finished_stock.quantity == 15
    assert output_movement.quantity_change == 5
    assert output_movement.quantity_after == 15


def test_transfer_confirm_rejects_user_outside_warehouse_departments(db):
    source_department = add_department(db, code="SRC", name="Source")
    destination_department = add_department(db, code="DST", name="Destination")
    unrelated_department = add_department(db, code="OTHER", name="Other")
    user = add_user(db, role="user")
    db.add(
        Employee(
            code="EMP-001",
            full_name="Other Department User",
            department_id=unrelated_department.id,
            user_id=user.id,
            is_active=True,
        )
    )
    source = add_warehouse(db, code="SRC-WH", name="Source Warehouse")
    destination = add_warehouse(db, code="DST-WH", name="Destination Warehouse")
    source.department_id = source_department.id
    destination.department_id = destination_department.id
    product = add_product(db)
    db.add(Stock(warehouse_id=source.id, product_id=product.id, quantity=20))
    transfer = WarehouseTransfer(
        number="TR-001",
        from_warehouse_id=source.id,
        to_warehouse_id=destination.id,
        status="pending_approval",
        user_id=user.id,
    )
    db.add(transfer)
    db.flush()
    db.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=5))
    db.commit()

    response = asyncio.run(warehouse_transfer_confirm(transfer.id, db=db, current_user=user))

    source_stock = db.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one()
    destination_stock = db.query(Stock).filter_by(warehouse_id=destination.id, product_id=product.id).first()
    movements = db.query(StockMovement).filter_by(document_id=transfer.id, document_type="WarehouseTransfer").all()
    assert response.status_code == 303
    assert "ruxsat" in response.headers["location"]
    assert transfer.status == "pending_approval"
    assert source_stock.quantity == 20
    assert destination_stock is None
    assert movements == []
