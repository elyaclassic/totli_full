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
    Production,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    User,
    Warehouse,
)
from app.utils.auth import create_session_token


def _new_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def test_stock_adjustment_confirm_and_revert_apply_only_the_delta():
    db = _new_session()
    try:
        user = User(username="admin", full_name="Admin", role="admin", is_active=True)
        warehouse = Warehouse(code="W1", name="Warehouse")
        product = Product(code="P1", name="Product")
        stock = Stock(warehouse=warehouse, product=product, quantity=100)
        doc = StockAdjustmentDoc(number="ADJ-1", status="draft", user=user)
        item = StockAdjustmentDocItem(doc=doc, product=product, warehouse=warehouse, quantity=150)
        db.add_all([user, warehouse, product, stock, doc, item])
        db.commit()

        asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))

        db.expire_all()
        stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
        assert stock.quantity == 150
        movement = db.query(StockMovement).filter_by(operation_type="adjustment").one()
        assert movement.quantity_change == 50
        assert movement.quantity_after == 150

        asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db, user))

        db.expire_all()
        stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
        assert stock.quantity == 100
        revert = db.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
        assert revert.quantity_change == -50
        assert revert.quantity_after == 100
    finally:
        db.close()


def test_production_completion_counts_output_once():
    db = _new_session()
    try:
        user = User(username="prod", full_name="Production", role="user", is_active=True)
        warehouse = Warehouse(code="W1", name="Warehouse")
        material = Product(code="M1", name="Material", purchase_price=2)
        output = Product(code="O1", name="Output", purchase_price=10)
        recipe = Recipe(product=output, name="Output recipe", output_quantity=1)
        recipe_item = RecipeItem(recipe=recipe, product=material, quantity=3)
        production = Production(
            number="PR-1",
            recipe=recipe,
            warehouse=warehouse,
            quantity=10,
            status="draft",
            user_id=1,
        )
        db.add_all([
            user,
            warehouse,
            material,
            output,
            recipe,
            recipe_item,
            production,
            Stock(warehouse=warehouse, product=material, quantity=100),
            Stock(warehouse=warehouse, product=output, quantity=5),
        ])
        db.commit()

        err = main._do_complete_production_stock(db, production, recipe)
        assert err is None
        db.commit()

        material_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
        output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
        assert material_stock.quantity == 70
        assert output_stock.quantity == 15
        output_movement = db.query(StockMovement).filter_by(operation_type="production_output").one()
        assert output_movement.quantity_change == 10
        assert output_movement.quantity_after == 15
    finally:
        db.close()


def test_pwa_location_routes_use_signed_token_identity_without_csrf_cookie():
    db = _new_session()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        agent = Agent(code="A1", full_name="Agent One", phone="+100", is_active=True)
        driver = Driver(code="D1", full_name="Driver One", phone="+200", vehicle_number="01A001", is_active=True)
        db.add_all([agent, driver])
        db.commit()

        client = TestClient(main.app)
        agent_token = create_session_token(agent.id, "agent")
        driver_token = create_session_token(driver.id, "driver")

        agent_response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.3",
                "longitude": "69.2",
                "accuracy": "5",
                "battery": "90",
                "token": agent_token,
            },
        )
        assert agent_response.status_code == 200
        assert agent_response.json()["success"] is True
        assert db.query(AgentLocation).one().agent_id == agent.id

        driver_response = client.post(
            "/api/driver/location",
            data={
                "latitude": "42.3",
                "longitude": "70.2",
                "accuracy": "7",
                "battery": "80",
                "token": driver_token,
            },
        )
        assert driver_response.status_code == 200
        assert driver_response.json()["success"] is True
        assert db.query(DriverLocation).one().driver_id == driver.id

        legacy_response = client.post(
            "/api/driver/location",
            data={"driver_code": "D1", "latitude": "1", "longitude": "2"},
        )
        assert legacy_response.status_code == 422
        assert db.query(DriverLocation).count() == 1
    finally:
        main.app.dependency_overrides.clear()
        db.close()
