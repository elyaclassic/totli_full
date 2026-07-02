import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models import database
from app.models.database import (
    Agent,
    AgentLocation,
    Driver,
    DriverLocation,
    Product,
    Production,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    Unit,
    User,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.utils.auth import create_session_token


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'totli-test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(main, "SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    original_startup = list(main.app.router.on_startup)
    main.app.router.on_startup.clear()
    main.app.dependency_overrides[database.get_db] = override_get_db
    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        main.app.router.on_startup[:] = original_startup


def test_mobile_location_uses_signed_subject_token_without_csrf(client, db_session):
    db_session.add_all([
        Agent(id=1, code="AG001", full_name="Wrong Agent", phone="111", is_active=True),
        Agent(id=2, code="AG002", full_name="Right Agent", phone="222", is_active=True),
        Driver(id=5, code="DR005", full_name="Driver", phone="555", is_active=True),
    ])
    db_session.commit()

    login = client.post("/api/agent/login", data={"username": "222", "password": "222"})
    assert login.status_code == 200
    agent_token = login.json()["token"]

    response = client.post(
        "/api/agent/location",
        data={
            "latitude": "41.31",
            "longitude": "69.24",
            "accuracy": "7",
            "battery": "88",
            "token": agent_token,
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    saved = db_session.query(AgentLocation).one()
    assert saved.agent_id == 2
    assert saved.latitude == 41.31

    web_token = create_session_token(2, "user")
    rejected = client.post(
        "/api/agent/location",
        data={"latitude": "1", "longitude": "2", "token": web_token},
    )
    assert rejected.status_code == 200
    assert rejected.json()["success"] is False
    assert db_session.query(AgentLocation).count() == 1

    legacy_driver_code = client.post(
        "/api/driver/location",
        data={"driver_code": "DR005", "latitude": "1", "longitude": "2"},
    )
    assert legacy_driver_code.status_code == 422
    assert db_session.query(DriverLocation).count() == 0

    driver_token = create_session_token(5, "driver")
    driver_response = client.post(
        "/api/driver/location",
        data={
            "latitude": "40.1",
            "longitude": "70.2",
            "accuracy": "3",
            "battery": "75",
            "speed": "44.5",
            "token": driver_token,
        },
    )
    assert driver_response.status_code == 200
    assert driver_response.json()["success"] is True

    driver_location = db_session.query(DriverLocation).one()
    assert driver_location.driver_id == 5
    assert driver_location.speed == 44.5


def test_mobile_token_cannot_authenticate_web_cookie(client, db_session):
    db_session.add_all([
        User(id=1, username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True),
        Agent(id=1, code="AG001", full_name="Agent", phone="111", is_active=True),
    ])
    db_session.commit()

    response = client.get(
        "/products",
        cookies={"session_token": create_session_token(1, "agent")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_stock_adjustment_sets_absolute_quantity_and_reverts_recorded_delta(db_session):
    user = User(id=1, username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    unit = Unit(id=1, code="kg", name="Kilogram")
    warehouse = Warehouse(id=1, code="WH", name="Warehouse", is_active=True)
    product = Product(id=1, code="P1", name="Product", type="product", unit_id=1, is_active=True)
    db_session.add_all([user, unit, warehouse, product, Stock(warehouse_id=1, product_id=1, quantity=10)])
    db_session.flush()
    doc = StockAdjustmentDoc(id=1, number="ADJ-1", user_id=1, status="draft")
    db_session.add(doc)
    db_session.add(StockAdjustmentDocItem(doc_id=1, product_id=1, warehouse_id=1, quantity=15))
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(1, db_session, user))

    stock = db_session.query(Stock).filter_by(warehouse_id=1, product_id=1).one()
    assert stock.quantity == 15
    movement = db_session.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert movement.quantity_change == 5
    assert movement.quantity_after == 15

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(1, db_session, user))

    assert stock.quantity == 10
    revert = db_session.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert.quantity_change == -5


def test_production_completion_does_not_double_add_output_and_is_idempotent(db_session):
    user = User(id=1, username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    unit = Unit(id=1, code="kg", name="Kilogram")
    warehouse = Warehouse(id=1, code="WH", name="Warehouse", is_active=True)
    material = Product(id=1, code="MAT", name="Material", type="material", unit_id=1, purchase_price=2, is_active=True)
    output = Product(id=2, code="OUT", name="Output", type="product", unit_id=1, purchase_price=4, is_active=True)
    recipe = Recipe(id=1, product_id=2, name="Recipe", output_quantity=1, is_active=True)
    recipe_item = RecipeItem(recipe_id=1, product_id=1, quantity=2)
    production = Production(id=1, number="PR-1", recipe_id=1, warehouse_id=1, quantity=5, status="draft", user_id=1)
    db_session.add_all([
        user,
        unit,
        warehouse,
        material,
        output,
        recipe,
        recipe_item,
        production,
        Stock(warehouse_id=1, product_id=1, quantity=20),
        Stock(warehouse_id=1, product_id=2, quantity=10),
    ])
    db_session.commit()

    asyncio.run(main.complete_production(1, db_session, user))
    asyncio.run(main.complete_production(1, db_session, user))

    material_stock = db_session.query(Stock).filter_by(warehouse_id=1, product_id=1).one()
    output_stock = db_session.query(Stock).filter_by(warehouse_id=1, product_id=2).one()
    assert material_stock.quantity == 10
    assert output_stock.quantity == 15
    assert db_session.query(StockMovement).filter_by(operation_type="production_output").count() == 1


def test_warehouse_transfer_requires_permission_and_claims_once(db_session):
    admin = User(id=1, username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    user = User(id=2, username="user", password_hash="x", full_name="User", role="user", is_active=True)
    unit = Unit(id=1, code="kg", name="Kilogram")
    product = Product(id=1, code="P1", name="Product", type="product", unit_id=1, is_active=True)
    source = Warehouse(id=1, code="SRC", name="Source", is_active=True)
    dest = Warehouse(id=2, code="DST", name="Dest", is_active=True)
    transfer = WarehouseTransfer(
        id=1,
        number="TR-1",
        from_warehouse_id=1,
        to_warehouse_id=2,
        status="pending_approval",
        user_id=2,
    )
    db_session.add_all([
        admin,
        user,
        unit,
        product,
        source,
        dest,
        Stock(warehouse_id=1, product_id=1, quantity=10),
        Stock(warehouse_id=2, product_id=1, quantity=0),
        transfer,
        WarehouseTransferItem(transfer_id=1, product_id=1, quantity=3),
    ])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(main.warehouse_transfer_confirm(1, db_session, user))
    assert exc_info.value.status_code == 403

    asyncio.run(main.warehouse_transfer_confirm(1, db_session, admin))
    asyncio.run(main.warehouse_transfer_confirm(1, db_session, admin))

    assert db_session.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 7
    assert db_session.query(Stock).filter_by(warehouse_id=2, product_id=1).one().quantity == 3
    assert db_session.query(StockMovement).filter_by(operation_type="transfer_out").count() == 1
    assert db_session.query(StockMovement).filter_by(operation_type="transfer_in").count() == 1
