import asyncio
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.database as dbm
from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Department,
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
    User,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.utils.auth import create_session_token


@pytest.fixture()
def app_with_db(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(dbm, "engine", engine)
    monkeypatch.setattr(dbm, "SessionLocal", TestingSessionLocal)

    import main

    monkeypatch.setattr(main, "SessionLocal", TestingSessionLocal)
    yield main, TestingSessionLocal

    if "main" in sys.modules:
        # Keep the imported app object for pytest, but remove test DB connections.
        engine.dispose()


def _seed_mobile_subjects(SessionLocal):
    db = SessionLocal()
    try:
        user = User(username="web", password_hash="secret", full_name="Web User", role="user", is_active=True)
        agent = Agent(code="A1", full_name="Agent One", phone="901", is_active=True)
        driver = Driver(code="D1", full_name="Driver One", phone="902", is_active=True)
        db.add_all([user, agent, driver])
        db.commit()
        db.refresh(user)
        db.refresh(agent)
        db.refresh(driver)
        return user.id, agent.id, driver.id
    finally:
        db.close()


def test_mobile_tokens_do_not_become_web_sessions(app_with_db):
    main, SessionLocal = app_with_db
    _user_id, agent_id, _driver_id = _seed_mobile_subjects(SessionLocal)
    token = create_session_token(agent_id, "agent")

    with TestClient(main.app) as client:
        client.cookies.set("session_token", token)
        response = client.get("/products", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_mobile_login_and_location_require_active_signed_subject(app_with_db):
    main, SessionLocal = app_with_db
    _user_id, agent_id, driver_id = _seed_mobile_subjects(SessionLocal)

    with TestClient(main.app) as client:
        agent_login = client.post("/api/agent/login", data={"username": "901", "password": "901"})
        assert agent_login.status_code == 200
        agent_body = agent_login.json()
        assert agent_body["success"] is True

        agent_location = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.3",
                "longitude": "69.2",
                "accuracy": "7",
                "battery": "80",
                "token": agent_body["token"],
            },
        )
        assert agent_location.status_code == 200
        assert agent_location.json()["success"] is True

        invalid_agent_location = client.post(
            "/api/agent/location",
            data={
                "latitude": "42.0",
                "longitude": "70.0",
                "token": create_session_token(agent_id, "driver"),
            },
        )
        assert invalid_agent_location.status_code == 200
        assert invalid_agent_location.json()["success"] is False

        driver_login = client.post("/api/driver/login", data={"username": "902", "password": "902"})
        assert driver_login.status_code == 200
        driver_body = driver_login.json()
        assert driver_body["success"] is True

        driver_location = client.post(
            "/api/driver/location",
            data={
                "latitude": "41.4",
                "longitude": "69.4",
                "accuracy": "5",
                "battery": "70",
                "speed": "33",
                "token": driver_body["token"],
            },
        )
        assert driver_location.status_code == 200
        assert driver_location.json()["success"] is True

    db = SessionLocal()
    try:
        agent_locations = db.query(AgentLocation).all()
        driver_locations = db.query(DriverLocation).all()
        assert len(agent_locations) == 1
        assert agent_locations[0].agent_id == agent_id
        assert len(driver_locations) == 1
        assert driver_locations[0].driver_id == driver_id
        assert driver_locations[0].speed == 33
    finally:
        db.close()


def test_stock_adjustment_sets_absolute_quantity_and_reverts_delta(app_with_db):
    main, SessionLocal = app_with_db
    db = SessionLocal()
    try:
        user = User(username="admin", password_hash="secret", full_name="Admin", role="admin", is_active=True)
        warehouse = Warehouse(code="W1", name="Warehouse")
        product = Product(code="P1", name="Product", is_active=True)
        db.add_all([user, warehouse, product])
        db.commit()
        db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
        doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
        db.add(doc)
        db.commit()
        db.add(StockAdjustmentDocItem(doc_id=doc.id, warehouse_id=warehouse.id, product_id=product.id, quantity=5))
        db.commit()

        asyncio.run(main.qoldiqlar_tovar_hujjat_confirm(doc.id, db=db, current_user=user))
        stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
        movement = db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment",
        ).one()
        assert stock.quantity == 5
        assert movement.quantity_change == -5
        assert movement.quantity_after == 5

        asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))
        db.refresh(stock)
        assert stock.quantity == 10
        assert db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment_revert",
        ).count() == 1
    finally:
        db.close()


def test_production_output_is_counted_once_and_direct_complete_is_idempotent(app_with_db):
    main, SessionLocal = app_with_db
    db = SessionLocal()
    try:
        user = User(username="prod", password_hash="secret", full_name="Prod", role="production", is_active=True)
        raw_wh = Warehouse(code="RAW", name="Raw")
        out_wh = Warehouse(code="OUT", name="Output")
        material = Product(code="M1", name="Material", is_active=True, purchase_price=2)
        output = Product(code="F1", name="Finished", is_active=True)
        db.add_all([user, raw_wh, out_wh, material, output])
        db.commit()
        recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=1, is_active=True)
        db.add(recipe)
        db.commit()
        db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
        production = Production(
            number="PR-1",
            recipe_id=recipe.id,
            warehouse_id=raw_wh.id,
            output_warehouse_id=out_wh.id,
            quantity=5,
            status="draft",
            user_id=user.id,
        )
        db.add_all([Stock(warehouse_id=raw_wh.id, product_id=material.id, quantity=10), production])
        db.commit()

        asyncio.run(main.complete_production(production.id, db=db, current_user=user))
        raw_stock = db.query(Stock).filter_by(warehouse_id=raw_wh.id, product_id=material.id).one()
        out_stock = db.query(Stock).filter_by(warehouse_id=out_wh.id, product_id=output.id).one()
        assert raw_stock.quantity == 0
        assert out_stock.quantity == 5

        asyncio.run(main.complete_production(production.id, db=db, current_user=user))
        db.refresh(raw_stock)
        db.refresh(out_stock)
        assert raw_stock.quantity == 0
        assert out_stock.quantity == 5
    finally:
        db.close()


def test_warehouse_transfer_confirm_requires_permission_and_applies_once(app_with_db):
    main, SessionLocal = app_with_db
    db = SessionLocal()
    try:
        admin = User(username="admin", password_hash="secret", full_name="Admin", role="admin", is_active=True)
        other = User(username="other", password_hash="secret", full_name="Other", role="user", is_active=True)
        department = Department(code="D", name="Dept")
        product = Product(code="P1", name="Product", is_active=True)
        db.add_all([admin, other, department, product])
        db.commit()
        source = Warehouse(code="SRC", name="Source", responsible_id=admin.id, department_id=department.id)
        dest = Warehouse(code="DST", name="Dest", responsible_id=admin.id, department_id=department.id)
        db.add_all([source, dest])
        db.commit()
        db.add(Stock(warehouse_id=source.id, product_id=product.id, quantity=10))
        transfer = WarehouseTransfer(
            number="OT-1",
            from_warehouse_id=source.id,
            to_warehouse_id=dest.id,
            status="pending_approval",
            user_id=other.id,
        )
        db.add(transfer)
        db.commit()
        db.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=4))
        db.commit()

        asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=other))
        source_stock = db.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one()
        assert source_stock.quantity == 10
        assert db.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).first() is None

        asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=admin))
        db.refresh(source_stock)
        dest_stock = db.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one()
        assert source_stock.quantity == 6
        assert dest_stock.quantity == 4

        asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=admin))
        db.refresh(source_stock)
        db.refresh(dest_stock)
        assert source_stock.quantity == 6
        assert dest_stock.quantity == 4
    finally:
        db.close()
