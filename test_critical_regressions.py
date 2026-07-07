import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.deps import get_current_user
from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Driver,
    DriverLocation,
    Employee,
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
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.utils.auth import create_session_token, hash_password


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'totli-test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def run_async(awaitable):
    return asyncio.run(awaitable)


def add_user(db, username="admin", role="admin", user_id=None):
    user = User(
        id=user_id,
        username=username,
        password_hash=hash_password("secret"),
        full_name=username.title(),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def add_product(db, name, product_type="product"):
    product = Product(name=name, type=product_type, is_active=True)
    db.add(product)
    db.flush()
    return product


def add_warehouse(db, name="Warehouse", responsible_id=None, department_id=None):
    warehouse = Warehouse(
        code=f"WH-{name}",
        name=name,
        responsible_id=responsible_id,
        department_id=department_id,
        is_active=True,
    )
    db.add(warehouse)
    db.flush()
    return warehouse


def test_stock_adjustment_sets_absolute_quantity_and_reverts_delta(db_session):
    admin = add_user(db_session)
    warehouse = add_warehouse(db_session)
    product = add_product(db_session, "Sugar")
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=admin.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=15,
        )
    )
    db_session.commit()

    run_async(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, admin))
    db_session.refresh(stock)
    assert stock.quantity == 15
    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 5
    assert movement.quantity_after == 15

    main.create_stock_movement(
        db_session,
        warehouse.id,
        product.id,
        10,
        "purchase",
        "Purchase",
        999,
        "P-999",
        admin.id,
        "later stock change",
    )
    db_session.commit()
    db_session.refresh(stock)
    assert stock.quantity == 25

    run_async(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, admin))
    db_session.refresh(stock)
    assert stock.quantity == 20
    assert db_session.query(StockMovement).filter_by(operation_type="adjustment_revert").count() == 1


def test_production_completion_is_not_double_applied_and_completed_rows_are_protected(db_session):
    admin = add_user(db_session)
    warehouse = add_warehouse(db_session)
    raw = add_product(db_session, "Raw", "material")
    output = add_product(db_session, "Halva", "product")
    db_session.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw.id, quantity=100),
        Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=0),
    ])
    recipe = Recipe(product_id=output.id, name="Halva recipe", output_quantity=1, is_active=True)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        output_warehouse_id=warehouse.id,
        quantity=5,
        status="draft",
        user_id=admin.id,
    )
    db_session.add(production)
    db_session.commit()

    run_async(main.complete_production(production.id, db_session, admin))
    raw_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw.id).one()
    output_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
    assert raw_stock.quantity == 90
    assert output_stock.quantity == 5

    run_async(main.complete_production(production.id, db_session, admin))
    db_session.refresh(raw_stock)
    db_session.refresh(output_stock)
    assert raw_stock.quantity == 90
    assert output_stock.quantity == 5

    run_async(main.cancel_production(production.id, db_session, admin))
    db_session.refresh(production)
    assert production.status == "completed"
    with pytest.raises(HTTPException):
        run_async(main.delete_production(production.id, db_session, admin))


def test_mobile_tokens_do_not_authenticate_web_and_location_routes_validate_subjects(db_session):
    user = add_user(db_session, username="web", role="user", user_id=1)
    agent = Agent(id=1, code="A1", full_name="Agent One", phone="100", is_active=True)
    driver = Driver(id=1, code="D1", full_name="Driver One", phone="200", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()

    agent_token = create_session_token(agent.id, "agent")
    driver_token = create_session_token(driver.id, "driver")
    assert get_current_user(session_token=agent_token, db=db_session) is None
    assert get_current_user(session_token=create_session_token(user.id, "user"), db=db_session).id == user.id

    def override_get_db():
        yield db_session

    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        client = TestClient(main.app)
        agent_response = client.post(
            "/api/agent/location",
            data={"latitude": 41.0, "longitude": 69.0, "token": agent_token},
        )
        assert agent_response.status_code == 200
        assert agent_response.json()["success"] is True
        assert db_session.query(AgentLocation).one().agent_id == agent.id

        invalid_agent_response = client.post(
            "/api/agent/location",
            data={"latitude": 42.0, "longitude": 70.0, "token": driver_token},
        )
        assert invalid_agent_response.status_code == 200
        assert invalid_agent_response.json()["success"] is False

        driver_response = client.post(
            "/api/driver/location",
            data={"latitude": 40.0, "longitude": 68.0, "speed": 35, "token": driver_token},
        )
        assert driver_response.status_code == 200
        assert driver_response.json()["success"] is True
        driver_location = db_session.query(DriverLocation).one()
        assert driver_location.driver_id == driver.id
        assert driver_location.speed == 35
    finally:
        main.app.dependency_overrides.clear()


def test_warehouse_transfer_requires_permission_and_is_idempotent(db_session):
    admin = add_user(db_session, username="admin", role="admin")
    stranger = add_user(db_session, username="stranger", role="user")
    source = add_warehouse(db_session, "Source")
    destination = add_warehouse(db_session, "Destination")
    product = add_product(db_session, "Product")
    db_session.add(Stock(warehouse_id=source.id, product_id=product.id, quantity=10))
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source.id,
        to_warehouse_id=destination.id,
        status="pending_approval",
        user_id=admin.id,
    )
    db_session.add(transfer)
    db_session.flush()
    db_session.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=4))
    db_session.commit()

    run_async(main.warehouse_transfer_confirm(transfer.id, db_session, stranger))
    db_session.refresh(transfer)
    source_stock = db_session.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one()
    assert transfer.status == "pending_approval"
    assert source_stock.quantity == 10

    run_async(main.warehouse_transfer_confirm(transfer.id, db_session, admin))
    db_session.refresh(transfer)
    db_session.refresh(source_stock)
    dest_stock = db_session.query(Stock).filter_by(warehouse_id=destination.id, product_id=product.id).one()
    assert transfer.status == "confirmed"
    assert source_stock.quantity == 6
    assert dest_stock.quantity == 4

    run_async(main.warehouse_transfer_confirm(transfer.id, db_session, admin))
    db_session.refresh(source_stock)
    db_session.refresh(dest_stock)
    assert source_stock.quantity == 6
    assert dest_stock.quantity == 4


def test_department_employee_can_confirm_transfer(db_session):
    user = add_user(db_session, username="dept-user", role="user")
    source = add_warehouse(db_session, "DeptSource", department_id=7)
    destination = add_warehouse(db_session, "DeptDestination")
    product = add_product(db_session, "DeptProduct")
    db_session.add_all([
        Employee(full_name="Dept Employee", user_id=user.id, department_id=7, is_active=True),
        Stock(warehouse_id=source.id, product_id=product.id, quantity=3),
    ])
    transfer = WarehouseTransfer(
        number="TR-2",
        from_warehouse_id=source.id,
        to_warehouse_id=destination.id,
        status="pending_approval",
        user_id=user.id,
    )
    db_session.add(transfer)
    db_session.flush()
    db_session.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=2))
    db_session.commit()

    run_async(main.warehouse_transfer_confirm(transfer.id, db_session, user))
    db_session.refresh(transfer)
    assert transfer.status == "confirmed"
