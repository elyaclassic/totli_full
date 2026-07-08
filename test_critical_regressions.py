import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Driver,
    DriverLocation,
    Employee,
    Product,
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
    Production,
)
from app.utils.auth import create_session_token


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()


def make_user(db, username="admin", role="admin"):
    user = User(username=username, password_hash="x", full_name=username, role=role, is_active=True)
    db.add(user)
    db.flush()
    return user


def make_product(db, name, product_type="product", purchase_price=0):
    product = Product(name=name, type=product_type, purchase_price=purchase_price, is_active=True)
    db.add(product)
    db.flush()
    return product


def make_warehouse(db, name, **kwargs):
    warehouse = Warehouse(name=name, is_active=True, **kwargs)
    db.add(warehouse)
    db.flush()
    return warehouse


def test_stock_adjustment_confirm_and_revert_apply_recorded_delta_once(db_session):
    admin = make_user(db_session)
    warehouse = make_warehouse(db_session, "Main")
    product = make_product(db_session, "Halva")
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=40))
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=admin.id, status="draft")
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

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, admin))

    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 50
    adjustment = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert adjustment.quantity_change == 10

    main.create_stock_movement(
        db=db_session,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity_change=5,
        operation_type="other",
        document_type="Manual",
        document_id=999,
    )
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, admin))

    db_session.refresh(stock)
    assert stock.quantity == 45
    revert = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert revert.quantity_change == -10


def test_production_completion_single_applies_and_is_idempotent(db_session):
    admin = make_user(db_session)
    raw_wh = make_warehouse(db_session, "Raw")
    output_wh = make_warehouse(db_session, "Output")
    material = make_product(db_session, "Sugar", product_type="material", purchase_price=2)
    finished = make_product(db_session, "Finished", purchase_price=10)
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1, is_active=True)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PROD-1",
        recipe_id=recipe.id,
        warehouse_id=raw_wh.id,
        output_warehouse_id=output_wh.id,
        quantity=5,
        status="draft",
        user_id=admin.id,
    )
    db_session.add_all(
        [
            production,
            Stock(warehouse_id=raw_wh.id, product_id=material.id, quantity=10),
            Stock(warehouse_id=output_wh.id, product_id=finished.id, quantity=100),
        ]
    )
    db_session.commit()

    asyncio.run(main.complete_production(production.id, db_session, admin))
    asyncio.run(main.complete_production(production.id, db_session, admin))

    raw_stock = db_session.query(Stock).filter_by(warehouse_id=raw_wh.id, product_id=material.id).one()
    output_stock = db_session.query(Stock).filter_by(warehouse_id=output_wh.id, product_id=finished.id).one()
    assert raw_stock.quantity == 0
    assert output_stock.quantity == 105
    output_movements = db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).all()
    assert [movement.quantity_change for movement in output_movements] == [5]


def test_mobile_location_uses_signed_active_subject_without_csrf(client, db_session):
    agent1 = Agent(code="A1", full_name="Agent One", phone="111", is_active=True)
    agent2 = Agent(code="A2", full_name="Agent Two", phone="222", is_active=True)
    driver = Driver(code="D1", full_name="Driver One", phone="333", vehicle_number="01A", is_active=True)
    db_session.add_all([agent1, agent2, driver])
    db_session.commit()

    response = client.post(
        "/api/agent/location",
        data={
            "latitude": 41.1,
            "longitude": 69.2,
            "accuracy": 8,
            "battery": 77,
            "token": create_session_token(agent2.id, "agent"),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    agent_location = db_session.query(AgentLocation).one()
    assert agent_location.agent_id == agent2.id

    response = client.post(
        "/api/driver/location",
        data={
            "latitude": 42.1,
            "longitude": 70.2,
            "accuracy": 6,
            "battery": 66,
            "speed": 55,
            "token": create_session_token(driver.id, "driver"),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    driver_location = db_session.query(DriverLocation).one()
    assert driver_location.driver_id == driver.id
    assert driver_location.speed == 55

    web_user = make_user(db_session, username="web", role="user")
    response = client.post(
        "/api/agent/location",
        data={
            "latitude": 40.0,
            "longitude": 68.0,
            "token": create_session_token(web_user.id, "user"),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is False
    assert db_session.query(AgentLocation).count() == 1

    response = client.post(
        "/api/driver/location",
        data={
            "driver_code": driver.code,
            "latitude": 40.0,
            "longitude": 68.0,
        },
    )
    assert response.status_code == 422
    assert db_session.query(DriverLocation).count() == 1


def test_warehouse_transfer_confirm_requires_permission_and_is_not_replayed(db_session, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    admin = make_user(db_session, username="admin", role="admin")
    outsider = make_user(db_session, username="outsider", role="user")
    approver = make_user(db_session, username="approver", role="user")
    source = make_warehouse(db_session, "Source", responsible_id=approver.id)
    dest = make_warehouse(db_session, "Dest")
    product = make_product(db_session, "Product")
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source.id,
        to_warehouse_id=dest.id,
        status="pending_approval",
        user_id=outsider.id,
    )
    db_session.add(transfer)
    db_session.flush()
    db_session.add_all(
        [
            WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=3),
            Stock(warehouse_id=source.id, product_id=product.id, quantity=10),
            Stock(warehouse_id=dest.id, product_id=product.id, quantity=0),
            Employee(full_name="Approver", user_id=approver.id, is_active=True),
        ]
    )
    db_session.commit()

    asyncio.run(main.warehouse_transfer_confirm(transfer.id, db_session, outsider))
    assert db_session.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one().quantity == 10
    assert db_session.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one().quantity == 0

    asyncio.run(main.warehouse_transfer_confirm(transfer.id, db_session, approver))
    asyncio.run(main.warehouse_transfer_confirm(transfer.id, db_session, admin))

    assert db_session.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one().quantity == 7
    assert db_session.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one().quantity == 3
    movements = db_session.query(StockMovement).filter_by(
        document_type="WarehouseTransfer",
        document_id=transfer.id,
    ).all()
    assert sorted(movement.quantity_change for movement in movements) == [-3, 3]
