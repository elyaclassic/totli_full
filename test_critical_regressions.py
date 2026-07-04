import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.deps import get_current_user
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
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.utils.auth import create_session_token
from main import (
    agent_location_update,
    agent_login,
    app,
    complete_production,
    driver_location_update,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
    warehouse_transfer_confirm,
)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def test_web_auth_rejects_mobile_token_even_when_ids_overlap():
    db = _session()
    try:
        user = User(id=1, username="admin", password_hash="x", role="admin", is_active=True)
        db.add(user)
        db.commit()

        assert get_current_user(create_session_token(1, "agent"), db) is None
        assert get_current_user(create_session_token(1, "driver"), db) is None
        assert get_current_user(create_session_token(1, "user"), db).id == 1
    finally:
        db.close()


def test_mobile_login_and_location_validate_signed_subjects():
    db = _session()
    try:
        agent1 = Agent(id=1, code="A1", full_name="Agent One", phone="111", is_active=True)
        agent2 = Agent(id=2, code="A2", full_name="Agent Two", phone="222", is_active=True)
        driver = Driver(id=1, code="D1", full_name="Driver One", phone="333", is_active=True)
        db.add_all([agent1, agent2, driver])
        db.commit()

        login = asyncio.run(agent_login(username="222", password="222", db=db))
        assert login["success"] is True

        result = asyncio.run(
            agent_location_update(
                latitude=41.0,
                longitude=69.0,
                accuracy=5,
                battery=88,
                token=login["token"],
                db=db,
            )
        )
        assert result["success"] is True
        location = db.query(AgentLocation).one()
        assert location.agent_id == agent2.id

        rejected = asyncio.run(
            driver_location_update(
                latitude=40.0,
                longitude=68.0,
                accuracy=8,
                battery=77,
                speed=12,
                token=login["token"],
                db=db,
            )
        )
        assert rejected["success"] is False

        driver_result = asyncio.run(
            driver_location_update(
                latitude=40.0,
                longitude=68.0,
                accuracy=8,
                battery=77,
                speed=12,
                token=create_session_token(driver.id, "driver"),
                db=db,
            )
        )
        assert driver_result["success"] is True
        driver_location = db.query(DriverLocation).one()
        assert driver_location.driver_id == driver.id
        assert driver_location.speed == 12
    finally:
        db.close()


def test_driver_location_route_is_not_shadowed_by_legacy_code_endpoint():
    live_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/driver/location" and "POST" in getattr(route, "methods", set())
    ]
    assert len(live_routes) == 1
    assert live_routes[0].endpoint.__name__ == "driver_location_update"


def test_stock_adjustment_sets_absolute_quantity_and_reverts_delta():
    db = _session()
    try:
        user = User(id=1, username="admin", password_hash="x", role="admin", is_active=True)
        product = Product(id=1, code="P1", name="Product", type="tayyor")
        warehouse = Warehouse(id=1, code="W1", name="Warehouse")
        stock = Stock(warehouse_id=1, product_id=1, quantity=5)
        doc = StockAdjustmentDoc(id=1, number="ADJ-1", user_id=1, status="draft")
        item = StockAdjustmentDocItem(doc_id=1, product_id=1, warehouse_id=1, quantity=8)
        db.add_all([user, product, warehouse, stock, doc, item])
        db.commit()

        asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc_id=1, db=db, current_user=user))
        db.expire_all()
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 8
        movement = db.query(StockMovement).filter_by(operation_type="adjustment").one()
        assert movement.quantity_change == 3
        assert movement.quantity_after == 8

        asyncio.run(qoldiqlar_tovar_hujjat_revert(doc_id=1, db=db, current_user=user))
        db.expire_all()
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 5
        revert = db.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
        assert revert.quantity_change == -3
        assert revert.quantity_after == 5
    finally:
        db.close()


def test_production_completion_is_idempotent_and_does_not_double_add_output():
    db = _session()
    try:
        user = User(id=1, username="maker", password_hash="x", role="production", is_active=True)
        material = Product(id=1, code="M1", name="Material", type="hom_ashyo", purchase_price=2)
        output = Product(id=2, code="F1", name="Finished", type="tayyor", purchase_price=10)
        warehouse = Warehouse(id=1, code="W1", name="Warehouse")
        recipe = Recipe(id=1, product_id=2, name="Recipe", output_quantity=5)
        recipe_item = RecipeItem(recipe_id=1, product_id=1, quantity=2)
        production = Production(id=1, number="PR-1", recipe_id=1, warehouse_id=1, quantity=1, status="draft", user_id=1)
        db.add_all([
            user,
            material,
            output,
            warehouse,
            recipe,
            recipe_item,
            production,
            Stock(warehouse_id=1, product_id=1, quantity=10),
            Stock(warehouse_id=1, product_id=2, quantity=1),
        ])
        db.commit()

        asyncio.run(complete_production(prod_id=1, db=db, current_user=user))
        db.expire_all()
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 8
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=2).one().quantity == 6

        asyncio.run(complete_production(prod_id=1, db=db, current_user=user))
        db.expire_all()
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 8
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=2).one().quantity == 6
    finally:
        db.close()


def test_warehouse_transfer_confirm_requires_permission_and_is_idempotent():
    db = _session()
    try:
        admin = User(id=1, username="admin", password_hash="x", role="admin", is_active=True)
        outsider = User(id=2, username="outsider", password_hash="x", role="user", is_active=True)
        product = Product(id=1, code="P1", name="Product", type="tayyor")
        wh1 = Warehouse(id=1, code="W1", name="From")
        wh2 = Warehouse(id=2, code="W2", name="To")
        transfer = WarehouseTransfer(
            id=1,
            number="TR-1",
            from_warehouse_id=1,
            to_warehouse_id=2,
            status="pending_approval",
            user_id=2,
        )
        item = WarehouseTransferItem(transfer_id=1, product_id=1, quantity=4)
        db.add_all([
            admin,
            outsider,
            product,
            wh1,
            wh2,
            transfer,
            item,
            Stock(warehouse_id=1, product_id=1, quantity=10),
        ])
        db.commit()

        asyncio.run(warehouse_transfer_confirm(transfer_id=1, db=db, current_user=outsider))
        db.expire_all()
        assert db.query(WarehouseTransfer).get(1).status == "pending_approval"
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 10

        asyncio.run(warehouse_transfer_confirm(transfer_id=1, db=db, current_user=admin))
        db.expire_all()
        assert db.query(WarehouseTransfer).get(1).status == "confirmed"
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 6
        assert db.query(Stock).filter_by(warehouse_id=2, product_id=1).one().quantity == 4

        asyncio.run(warehouse_transfer_confirm(transfer_id=1, db=db, current_user=admin))
        db.expire_all()
        assert db.query(Stock).filter_by(warehouse_id=1, product_id=1).one().quantity == 6
        assert db.query(Stock).filter_by(warehouse_id=2, product_id=1).one().quantity == 4
    finally:
        db.close()
