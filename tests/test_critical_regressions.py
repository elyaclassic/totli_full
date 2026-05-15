import asyncio

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
    Product,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    User,
    Warehouse,
)


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db(session_factory):
    def _override():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    return _override


def test_mobile_agent_location_uses_token_without_csrf():
    session_factory = _session_factory()
    db = session_factory()
    db.add(Agent(id=11, code="A011", full_name="Agent One", phone="+998901111111", is_active=True))
    db.commit()

    main.app.dependency_overrides[main.get_db] = _override_get_db(session_factory)
    try:
        client = TestClient(main.app)

        login = client.post(
            "/api/agent/login",
            data={"username": "+998901111111", "password": "+998901111111"},
        )
        assert login.status_code == 200
        token = login.json()["token"]

        response = client.post(
            "/api/agent/location",
            data={
                "latitude": 41.311081,
                "longitude": 69.240562,
                "accuracy": 10,
                "battery": 90,
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        location = db.query(AgentLocation).one()
        assert location.agent_id == 11
    finally:
        main.app.dependency_overrides.clear()
        db.close()


def test_mobile_driver_location_requires_driver_token():
    session_factory = _session_factory()
    db = session_factory()
    db.add(
        Driver(
            id=21,
            code="D021",
            full_name="Driver One",
            phone="+998902222222",
            vehicle_number="01A001AA",
            is_active=True,
        )
    )
    db.commit()

    main.app.dependency_overrides[main.get_db] = _override_get_db(session_factory)
    try:
        client = TestClient(main.app)

        code_only = client.post(
            "/api/driver/location",
            data={
                "driver_code": "D021",
                "latitude": 41.0,
                "longitude": 69.0,
            },
        )
        assert code_only.status_code == 422
        assert db.query(DriverLocation).count() == 0

        login = client.post(
            "/api/driver/login",
            data={"username": "+998902222222", "password": "+998902222222"},
        )
        assert login.status_code == 200
        token = login.json()["token"]

        response = client.post(
            "/api/driver/location",
            data={
                "latitude": 41.1,
                "longitude": 69.1,
                "accuracy": 8,
                "battery": 85,
                "speed": 45,
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        location = db.query(DriverLocation).one()
        assert location.driver_id == 21
    finally:
        main.app.dependency_overrides.clear()
        db.close()


def test_stock_adjustment_confirm_sets_target_and_revert_restores_previous_stock():
    session_factory = _session_factory()
    db = session_factory()
    admin = User(id=1, username="admin", full_name="Admin", role="admin", is_active=True)
    warehouse = Warehouse(id=1, code="WH1", name="Main warehouse", is_active=True)
    product = Product(id=1, code="P1", name="Halva", type="product", is_active=True)
    stock = Stock(id=1, warehouse_id=1, product_id=1, quantity=100)
    doc = StockAdjustmentDoc(id=1, number="QLD-TEST-1", user_id=1, status="draft")
    item = StockAdjustmentDocItem(doc_id=1, warehouse_id=1, product_id=1, quantity=150)
    db.add_all([admin, warehouse, product, stock, doc, item])
    db.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(1, db, admin))
    db.refresh(stock)
    assert stock.quantity == 150
    assert doc.status == "confirmed"

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(1, db, admin))
    db.refresh(stock)
    assert stock.quantity == 100
    assert doc.status == "draft"

    db.close()
