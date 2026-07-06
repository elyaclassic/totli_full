import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.deps import get_current_user
from app.models.database import (
    Base,
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
    User,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.utils.auth import create_session_token


@pytest.fixture
def db_factory(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(main, "SessionLocal", TestingSessionLocal)
    yield TestingSessionLocal
    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_factory):
    def override_get_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client


def _user(db, user_id=1, role="admin", phone="+100"):
    user = User(
        id=user_id,
        username=f"user{user_id}",
        password_hash="pw",
        full_name=f"User {user_id}",
        role=role,
        phone=phone,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _product(db, product_id, name):
    product = Product(id=product_id, code=f"P{product_id}", name=name, type="product", is_active=True)
    db.add(product)
    db.flush()
    return product


def _warehouse(db, warehouse_id, name, responsible_id=None, department_id=None):
    warehouse = Warehouse(
        id=warehouse_id,
        code=f"W{warehouse_id}",
        name=name,
        responsible_id=responsible_id,
        department_id=department_id,
        is_active=True,
    )
    db.add(warehouse)
    db.flush()
    return warehouse


def test_stock_adjustment_sets_absolute_quantity_and_reverts_from_movement(db_factory):
    db = db_factory()
    try:
        user = _user(db)
        product = _product(db, 1, "Flour")
        warehouse = _warehouse(db, 1, "Main")
        stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
        doc = StockAdjustmentDoc(number="ADJ-1", status="draft", user_id=user.id)
        db.add_all([stock, doc])
        db.flush()
        db.add(StockAdjustmentDocItem(doc=doc, product_id=product.id, warehouse_id=warehouse.id, quantity=50))
        db.commit()

        asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))

        db.refresh(stock)
        assert stock.quantity == 50
        movement = db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment",
        ).one()
        assert movement.quantity_change == 40

        asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))

        db.refresh(stock)
        assert stock.quantity == 10
        revert = db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment_revert",
        ).one()
        assert revert.quantity_change == -40
    finally:
        db.close()


def test_production_completion_outputs_once_and_is_idempotent(db_factory):
    db = db_factory()
    try:
        user = _user(db)
        material = _product(db, 1, "Sugar")
        output = _product(db, 2, "Candy")
        warehouse = _warehouse(db, 1, "Production")
        db.add(Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=100))
        recipe = Recipe(product_id=output.id, name="Candy recipe", output_quantity=1)
        db.add(recipe)
        db.flush()
        db.add(RecipeItem(recipe=recipe, product_id=material.id, quantity=2))
        production = Production(
            number="PR-1",
            recipe_id=recipe.id,
            warehouse_id=warehouse.id,
            output_warehouse_id=warehouse.id,
            quantity=5,
            status="draft",
            user_id=user.id,
        )
        db.add(production)
        db.commit()

        asyncio.run(main.complete_production(production.id, db=db, current_user=user))

        material_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
        output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
        assert material_stock.quantity == 90
        assert output_stock.quantity == 5

        asyncio.run(main.complete_production(production.id, db=db, current_user=user))

        db.refresh(material_stock)
        db.refresh(output_stock)
        assert material_stock.quantity == 90
        assert output_stock.quantity == 5
        assert db.query(StockMovement).filter_by(
            document_type="Production",
            document_id=production.id,
            operation_type="production_output",
        ).count() == 1
    finally:
        db.close()


def test_mobile_locations_require_active_signed_subject_tokens(client, db_factory):
    db = db_factory()
    try:
        db.add_all([
            Agent(id=7, code="A7", full_name="Agent Seven", phone="+777", is_active=True),
            Driver(id=8, code="D8", full_name="Driver Eight", phone="+888", vehicle_number="CAR8", is_active=True),
        ])
        db.commit()
    finally:
        db.close()

    bad = client.post("/api/agent/location", data={
        "latitude": 1,
        "longitude": 2,
        "token": "not-a-token",
    })
    assert bad.status_code == 200
    assert bad.json()["success"] is False

    agent_login = client.post("/api/agent/login", data={"username": "+777", "password": "+777"})
    assert agent_login.status_code == 200
    agent_token = agent_login.json()["token"]
    agent_location = client.post("/api/agent/location", data={
        "latitude": 41.0,
        "longitude": 69.0,
        "accuracy": 5,
        "battery": 80,
        "token": agent_token,
    })
    assert agent_location.status_code == 200
    assert agent_location.json()["success"] is True

    driver_login = client.post("/api/driver/login", data={"username": "+888", "password": "+888"})
    assert driver_login.status_code == 200
    driver_token = driver_login.json()["token"]
    driver_location = client.post("/api/driver/location", data={
        "latitude": 42.0,
        "longitude": 70.0,
        "speed": 55,
        "token": driver_token,
    })
    assert driver_location.status_code == 200
    assert driver_location.json()["success"] is True

    db = db_factory()
    try:
        assert db.query(AgentLocation).one().agent_id == 7
        driver_row = db.query(DriverLocation).one()
        assert driver_row.driver_id == 8
        assert driver_row.speed == 55
    finally:
        db.close()


def test_mobile_tokens_do_not_authenticate_as_web_users(db_factory):
    db = db_factory()
    try:
        _user(db, user_id=1, role="admin")
        db.add(Agent(id=1, code="A1", full_name="Agent One", phone="+111", is_active=True))
        db.commit()
        token = create_session_token(1, "agent")

        assert get_current_user(session_token=token, db=db) is None
    finally:
        db.close()


def test_warehouse_transfer_confirm_requires_permission_and_is_idempotent(db_factory):
    db = db_factory()
    try:
        owner = _user(db, user_id=1, role="user")
        outsider = _user(db, user_id=2, role="user", phone="+200")
        product = _product(db, 1, "Boxes")
        source = _warehouse(db, 1, "Source", responsible_id=owner.id)
        dest = _warehouse(db, 2, "Dest")
        db.add(Stock(warehouse_id=source.id, product_id=product.id, quantity=20))
        transfer = WarehouseTransfer(
            number="TR-1",
            from_warehouse_id=source.id,
            to_warehouse_id=dest.id,
            status="pending_approval",
            user_id=owner.id,
        )
        db.add(transfer)
        db.flush()
        db.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=5))
        db.commit()

        asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=outsider))
        db.refresh(transfer)
        assert transfer.status == "pending_approval"
        assert db.query(StockMovement).count() == 0

        asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=owner))
        source_stock = db.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one()
        dest_stock = db.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one()
        assert source_stock.quantity == 15
        assert dest_stock.quantity == 5

        asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=owner))
        db.refresh(source_stock)
        db.refresh(dest_stock)
        assert source_stock.quantity == 15
        assert dest_stock.quantity == 5
        assert db.query(StockMovement).filter_by(document_type="WarehouseTransfer", document_id=transfer.id).count() == 2
    finally:
        db.close()
