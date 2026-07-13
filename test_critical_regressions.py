import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
from app.utils.auth import create_session_token


def _db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _user(db, role="admin", username="admin", user_id=None):
    user = User(
        id=user_id,
        username=username,
        password_hash="pw",
        full_name=username,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _product(db, code, name, product_type="material"):
    product = Product(code=code, name=name, type=product_type, purchase_price=10)
    db.add(product)
    db.commit()
    return product


def _warehouse(db, code, name, **kwargs):
    warehouse = Warehouse(code=code, name=name, **kwargs)
    db.add(warehouse)
    db.commit()
    return warehouse


def test_stock_adjustment_confirm_and_revert_apply_delta_once():
    db = _db_session()
    admin = _user(db)
    warehouse = _warehouse(db, "WH1", "Main")
    product = _product(db, "P1", "Halva")
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=admin.id, status="draft")
    db.add_all([stock, doc])
    db.commit()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
        )
    )
    db.commit()

    asyncio.run(
        main.qoldiqlar_tovar_hujjat_tasdiqlash(
            doc_id=doc.id,
            db=db,
            current_user=admin,
        )
    )

    db.refresh(stock)
    assert stock.quantity == 50
    movement = db.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert movement.quantity_change == 40
    assert movement.quantity_after == 50

    asyncio.run(
        main.qoldiqlar_tovar_hujjat_revert(
            doc_id=doc.id,
            db=db,
            current_user=admin,
        )
    )

    db.refresh(stock)
    assert stock.quantity == 10
    revert = db.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert.quantity_change == -40


def test_production_completion_adds_output_once_and_is_idempotent(monkeypatch):
    db = _db_session()
    admin = _user(db)
    warehouse = _warehouse(db, "WH1", "Main")
    material = _product(db, "M1", "Sugar")
    finished = _product(db, "F1", "Finished", product_type="product")
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1)
    db.add(recipe)
    db.commit()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=5,
        status="draft",
        user_id=admin.id,
    )
    db.add_all(
        [
            Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=10),
            Stock(warehouse_id=warehouse.id, product_id=finished.id, quantity=0),
            production,
        ]
    )
    db.commit()
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda db: None)

    asyncio.run(main.complete_production(prod_id=production.id, db=db, current_user=admin))
    material_stock = db.query(Stock).filter_by(product_id=material.id).one()
    finished_stock = db.query(Stock).filter_by(product_id=finished.id).one()
    assert material_stock.quantity == 0
    assert finished_stock.quantity == 5

    asyncio.run(main.complete_production(prod_id=production.id, db=db, current_user=admin))
    db.refresh(material_stock)
    db.refresh(finished_stock)
    assert material_stock.quantity == 0
    assert finished_stock.quantity == 5


def test_mobile_location_uses_signed_active_subject_and_single_driver_route():
    db = _db_session()
    agent = Agent(id=7, code="A7", full_name="Agent 7", phone="700", is_active=True)
    driver = Driver(id=8, code="D8", full_name="Driver 8", phone="800", is_active=True)
    db.add_all([agent, driver])
    db.commit()

    agent_token = create_session_token(agent.id, "agent")
    result = asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            accuracy=5,
            battery=90,
            token=agent_token,
            db=db,
        )
    )
    assert result["success"] is True
    assert db.query(AgentLocation).one().agent_id == agent.id

    driver_token = create_session_token(driver.id, "driver")
    result = asyncio.run(
        main.driver_location_update(
            latitude=42.0,
            longitude=70.0,
            accuracy=4,
            battery=80,
            speed=55,
            token=driver_token,
            db=db,
        )
    )
    assert result["success"] is True
    driver_location = db.query(DriverLocation).one()
    assert driver_location.driver_id == driver.id
    assert driver_location.speed == 55

    routes = [
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(routes) == 1
    assert routes[0].endpoint.__name__ == "driver_location_update"


def test_mobile_token_cannot_authenticate_as_web_user_with_same_id():
    db = _db_session()
    user = _user(db, role="admin", username="web", user_id=1)
    db.add(Agent(id=1, code="A1", full_name="Agent 1", phone="100", is_active=True))
    db.commit()

    assert get_current_user(session_token=create_session_token(1, "agent"), db=db) is None
    assert get_current_user(session_token=create_session_token(user.id, "user"), db=db).id == user.id


def test_transfer_revert_requires_destination_stock_to_avoid_inventory_creation():
    db = _db_session()
    admin = _user(db)
    source = _warehouse(db, "SRC", "Source")
    dest = _warehouse(db, "DST", "Destination")
    product = _product(db, "P1", "Product")
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source.id,
        to_warehouse_id=dest.id,
        status="confirmed",
        user_id=admin.id,
    )
    db.add_all(
        [
            transfer,
            Stock(warehouse_id=source.id, product_id=product.id, quantity=0),
            Stock(warehouse_id=dest.id, product_id=product.id, quantity=20),
        ]
    )
    db.commit()
    db.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=100))
    db.commit()

    asyncio.run(
        main.warehouse_transfer_revert(
            transfer_id=transfer.id,
            db=db,
            current_user=admin,
        )
    )

    assert db.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one().quantity == 0
    assert db.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one().quantity == 20
    db.refresh(transfer)
    assert transfer.status == "confirmed"
