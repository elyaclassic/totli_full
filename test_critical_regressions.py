import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Driver,
    DriverLocation,
    Product,
    Production,
    Purchase,
    PurchaseItem,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    User,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.utils.auth import create_session_token


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
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


def run_async(coro):
    return asyncio.run(coro)


def make_user(db_session, role="admin"):
    user = User(username=f"{role}_user", password_hash="x", full_name="Admin", role=role, is_active=True)
    db_session.add(user)
    db_session.commit()
    return user


def make_product(db_session, code, name=None):
    product = Product(code=code, name=name or code, type="product", is_active=True)
    db_session.add(product)
    db_session.commit()
    return product


def make_warehouse(db_session, code):
    warehouse = Warehouse(code=code, name=code, is_active=True)
    db_session.add(warehouse)
    db_session.commit()
    return warehouse


def test_stock_adjustment_confirm_and_revert_apply_only_recorded_delta(db_session):
    user = make_user(db_session)
    product = make_product(db_session, "P-ADJ")
    warehouse = make_warehouse(db_session, "W-ADJ")
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add(doc)
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

    run_async(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))
    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 15

    run_async(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))
    db_session.refresh(stock)
    assert stock.quantity == 10


def test_production_complete_is_idempotent_and_adds_output_once(db_session):
    user = make_user(db_session)
    raw = make_product(db_session, "RAW")
    output = make_product(db_session, "OUT")
    source_wh = make_warehouse(db_session, "SRC")
    output_wh = make_warehouse(db_session, "OUT-WH")
    db_session.add(Stock(warehouse_id=source_wh.id, product_id=raw.id, quantity=100))
    db_session.add(Stock(warehouse_id=output_wh.id, product_id=output.id, quantity=7))
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=2, is_active=True)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=3))
    production = Production(
        number="PROD-1",
        recipe_id=recipe.id,
        warehouse_id=source_wh.id,
        output_warehouse_id=output_wh.id,
        quantity=4,
        status="draft",
        current_stage=1,
        user_id=user.id,
    )
    db_session.add(production)
    db_session.commit()

    run_async(main.complete_production(production.id, db_session, user))
    raw_stock = db_session.query(Stock).filter_by(warehouse_id=source_wh.id, product_id=raw.id).one()
    output_stock = db_session.query(Stock).filter_by(warehouse_id=output_wh.id, product_id=output.id).one()
    assert raw_stock.quantity == 88
    assert output_stock.quantity == 15

    run_async(main.complete_production(production.id, db_session, user))
    db_session.refresh(raw_stock)
    db_session.refresh(output_stock)
    assert raw_stock.quantity == 88
    assert output_stock.quantity == 15


def test_transfer_revert_does_not_create_missing_destination_stock(db_session):
    user = make_user(db_session)
    product = make_product(db_session, "P-TR")
    source_wh = make_warehouse(db_session, "A")
    dest_wh = make_warehouse(db_session, "B")
    db_session.add(Stock(warehouse_id=source_wh.id, product_id=product.id, quantity=0))
    db_session.add(Stock(warehouse_id=dest_wh.id, product_id=product.id, quantity=2))
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source_wh.id,
        to_warehouse_id=dest_wh.id,
        status="confirmed",
        user_id=user.id,
    )
    db_session.add(transfer)
    db_session.flush()
    db_session.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=10))
    db_session.commit()

    run_async(main.warehouse_transfer_revert(transfer.id, db_session, user))
    source_stock = db_session.query(Stock).filter_by(warehouse_id=source_wh.id, product_id=product.id).one()
    dest_stock = db_session.query(Stock).filter_by(warehouse_id=dest_wh.id, product_id=product.id).one()
    db_session.refresh(transfer)
    assert source_stock.quantity == 0
    assert dest_stock.quantity == 2
    assert transfer.status == "confirmed"


def test_confirmed_purchase_cannot_be_mutated_by_add_item(db_session):
    product = make_product(db_session, "P-PUR")
    warehouse = make_warehouse(db_session, "W-PUR")
    purchase = Purchase(number="PUR-1", warehouse_id=warehouse.id, status="confirmed", total=100)
    db_session.add(purchase)
    db_session.flush()
    db_session.add(PurchaseItem(purchase_id=purchase.id, product_id=product.id, quantity=10, price=10, total=100))
    db_session.commit()

    with pytest.raises(HTTPException):
        run_async(main.purchase_add_item(purchase.id, product.id, 5, 10, db_session))

    db_session.refresh(purchase)
    assert purchase.total == 100
    assert db_session.query(PurchaseItem).filter_by(purchase_id=purchase.id).count() == 1


def test_pwa_login_and_location_use_signed_mobile_tokens(db_session, client):
    agent = Agent(code="A-1", full_name="Agent One", phone="+100", is_active=True)
    other_agent = Agent(code="A-2", full_name="Agent Two", phone="+200", is_active=True)
    driver = Driver(code="D-1", full_name="Driver One", phone="+300", is_active=True)
    db_session.add_all([agent, other_agent, driver])
    db_session.commit()

    login_response = client.post("/api/agent/login", data={"username": "+100", "password": "+100"})
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["success"] is True
    assert login_data["user"]["agent"]["id"] == agent.id
    assert login_data["token"]

    invalid_response = client.post(
        "/api/agent/location",
        data={"latitude": 41.0, "longitude": 69.0, "accuracy": 1, "battery": 90, "token": "bad-token"},
    )
    assert invalid_response.status_code == 200
    assert invalid_response.json()["success"] is False
    assert db_session.query(AgentLocation).count() == 0

    valid_response = client.post(
        "/api/agent/location",
        data={
            "latitude": 41.1,
            "longitude": 69.1,
            "accuracy": 5,
            "battery": 80,
            "token": login_data["token"],
        },
    )
    assert valid_response.status_code == 200
    assert valid_response.json()["success"] is True
    saved_agent_location = db_session.query(AgentLocation).one()
    assert saved_agent_location.agent_id == agent.id

    driver_token = create_session_token(driver.id, "driver")
    driver_response = client.post(
        "/api/driver/location",
        data={
            "latitude": 40.5,
            "longitude": 68.5,
            "accuracy": 3,
            "battery": 70,
            "token": driver_token,
        },
    )
    assert driver_response.status_code == 200
    assert driver_response.json()["success"] is True
    saved_driver_location = db_session.query(DriverLocation).one()
    assert saved_driver_location.driver_id == driver.id
