import asyncio

import pytest
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
)
from app.utils.auth import create_session_token


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def run(coro):
    return asyncio.run(coro)


def add_user(db, username="admin", role="admin"):
    user = User(username=username, password_hash="x", full_name=username, role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_product(db, code, name):
    product = Product(code=code, name=name, type="tayyor", purchase_price=10, sale_price=20, is_active=True)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_warehouse(db, code, name, responsible_id=None):
    warehouse = Warehouse(code=code, name=name, responsible_id=responsible_id, is_active=True)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def stock_qty(db, warehouse_id, product_id):
    stock = db.query(Stock).filter(Stock.warehouse_id == warehouse_id, Stock.product_id == product_id).first()
    return stock.quantity if stock else 0


def test_stock_adjustment_sets_absolute_quantity_and_reverts_recorded_delta(db):
    admin = add_user(db)
    warehouse = add_warehouse(db, "W1", "Main")
    product = add_product(db, "P1", "Sugar")
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    db.commit()

    doc = StockAdjustmentDoc(number="ADJ-1", user_id=admin.id, status="draft")
    db.add(doc)
    db.commit()
    db.add(StockAdjustmentDocItem(doc_id=doc.id, warehouse_id=warehouse.id, product_id=product.id, quantity=15))
    db.commit()

    run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=admin))
    assert stock_qty(db, warehouse.id, product.id) == 15
    movement = db.query(StockMovement).filter(StockMovement.document_id == doc.id).one()
    assert movement.quantity_change == 5
    assert movement.quantity_after == 15

    run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=admin))
    assert stock_qty(db, warehouse.id, product.id) == 10
    revert = db.query(StockMovement).filter(StockMovement.operation_type == "adjustment_revert").one()
    assert revert.quantity_change == -5


def test_production_completion_outputs_once_and_is_idempotent(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    user = add_user(db)
    raw = add_product(db, "RAW", "Raw")
    finished = add_product(db, "FIN", "Finished")
    warehouse = add_warehouse(db, "W1", "Production")
    db.add(Stock(warehouse_id=warehouse.id, product_id=raw.id, quantity=20))
    db.commit()

    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1, is_active=True)
    db.add(recipe)
    db.commit()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=2))
    db.commit()
    production = main.Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=5,
        status="draft",
        user_id=user.id,
    )
    db.add(production)
    db.commit()

    run(main.complete_production(production.id, db=db, current_user=user))
    assert stock_qty(db, warehouse.id, raw.id) == 10
    assert stock_qty(db, warehouse.id, finished.id) == 5

    run(main.complete_production(production.id, db=db, current_user=user))
    assert stock_qty(db, warehouse.id, raw.id) == 10
    assert stock_qty(db, warehouse.id, finished.id) == 5

    run(main.cancel_production(production.id, db=db, current_user=user))
    assert db.query(main.Production).filter(main.Production.id == production.id).one().status == "completed"

    run(main.delete_production(production.id, db=db, current_user=user))
    assert db.query(main.Production).filter(main.Production.id == production.id).count() == 1


def test_mobile_tokens_cannot_authenticate_web_users_and_locations_use_signed_subject(db):
    user = add_user(db, username="web", role="user")
    agent = Agent(code="AG1", full_name="Agent", phone="100", is_active=True)
    driver = Driver(code="DR1", full_name="Driver", phone="200", is_active=True)
    db.add_all([agent, driver])
    db.commit()
    db.refresh(agent)
    db.refresh(driver)

    assert get_current_user(session_token=create_session_token(user.id, "agent"), db=db) is None
    assert get_current_user(session_token=create_session_token(user.id, "user"), db=db).id == user.id

    result = run(main.agent_location_update(
        latitude=41.0,
        longitude=69.0,
        accuracy=5,
        battery=80,
        token=create_session_token(agent.id, "agent"),
        db=db,
    ))
    assert result["success"] is True
    assert db.query(AgentLocation).one().agent_id == agent.id

    result = run(main.driver_location_update(
        latitude=42.0,
        longitude=70.0,
        accuracy=5,
        battery=75,
        speed=12,
        token=create_session_token(driver.id, "driver"),
        db=db,
    ))
    assert result["success"] is True
    driver_location = db.query(DriverLocation).one()
    assert driver_location.driver_id == driver.id
    assert driver_location.speed == 12

    bad = run(main.driver_location_update(
        latitude=42.0,
        longitude=70.0,
        accuracy=None,
        battery=None,
        speed=0,
        token=create_session_token(agent.id, "agent"),
        db=db,
    ))
    assert bad["success"] is False


def test_live_driver_location_route_is_not_shadowed_by_legacy_driver_code_handler():
    routes = [
        route for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(routes) == 1
    assert routes[0].endpoint is main.driver_location_update


def test_warehouse_transfer_requires_permission_and_confirms_once(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    admin = add_user(db, username="admin", role="admin")
    outsider = add_user(db, username="outsider", role="user")
    product = add_product(db, "P1", "Product")
    source = add_warehouse(db, "SRC", "Source")
    dest = add_warehouse(db, "DST", "Dest")
    db.add(Stock(warehouse_id=source.id, product_id=product.id, quantity=10))
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source.id,
        to_warehouse_id=dest.id,
        status="pending_approval",
        user_id=admin.id,
    )
    db.add(transfer)
    db.commit()
    db.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=3))
    db.commit()

    run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=outsider))
    assert stock_qty(db, source.id, product.id) == 10
    assert stock_qty(db, dest.id, product.id) == 0

    run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=admin))
    assert stock_qty(db, source.id, product.id) == 7
    assert stock_qty(db, dest.id, product.id) == 3

    run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=admin))
    assert stock_qty(db, source.id, product.id) == 7
    assert stock_qty(db, dest.id, product.id) == 3
