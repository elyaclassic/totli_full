import asyncio

import pytest
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


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _add_user(db_session, role="admin"):
    user = User(username=f"{role}_user", full_name="Test User", role=role, is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_stock_adjustment_confirm_and_revert_apply_single_delta(db_session):
    user = _add_user(db_session)
    warehouse = Warehouse(code="WH", name="Main")
    product = Product(code="P1", name="Product 1", type="product")
    db_session.add_all([warehouse, product])
    db_session.commit()

    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.commit()
    item = StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=80,
    )
    db_session.add(item)
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert doc.status == "confirmed"
    assert stock.quantity == 80
    assert movement.quantity_change == -20
    assert movement.quantity_after == 80

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    revert_movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert doc.status == "draft"
    assert stock.quantity == 100
    assert revert_movement.quantity_change == 20
    assert revert_movement.quantity_after == 100


def test_production_completion_adds_finished_goods_once(db_session):
    user = _add_user(db_session)
    warehouse = Warehouse(code="WH", name="Main")
    raw = Product(code="RAW", name="Raw", type="material", purchase_price=5)
    finished = Product(code="FIN", name="Finished", type="product", purchase_price=10)
    db_session.add_all([warehouse, raw, finished])
    db_session.commit()

    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1)
    db_session.add(recipe)
    db_session.commit()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=3,
        user_id=user.id,
    )
    db_session.add(production)
    db_session.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw.id, quantity=10),
        Stock(warehouse_id=warehouse.id, product_id=finished.id, quantity=5),
    ])
    db_session.commit()
    production_id = production.id

    result = main._do_complete_production_stock(db_session, production, recipe)

    assert result is None
    db_session.flush()
    raw_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw.id).one()
    finished_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=finished.id).one()
    output_movement = db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production_id,
        operation_type="production_output",
    ).one()
    assert raw_stock.quantity == 4
    assert finished_stock.quantity == 8
    assert output_movement.quantity_change == 3
    assert output_movement.quantity_after == 8


def test_pwa_location_endpoints_require_matching_signed_token(db_session):
    agent = Agent(code="A1", full_name="Agent One", phone="100", is_active=True)
    driver = Driver(code="D1", full_name="Driver One", phone="200", vehicle_number="01A001", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()
    db_session.refresh(agent)
    db_session.refresh(driver)

    invalid_agent_result = asyncio.run(main.agent_location_update(
        latitude=41.0,
        longitude=69.0,
        accuracy=None,
        battery=90,
        token=create_session_token(driver.id, "driver"),
        db=db_session,
    ))
    assert invalid_agent_result == {"success": False, "error": "Invalid token"}
    assert db_session.query(AgentLocation).count() == 0

    agent_result = asyncio.run(main.agent_location_update(
        latitude=41.0,
        longitude=69.0,
        accuracy=None,
        battery=90,
        token=create_session_token(agent.id, "agent"),
        db=db_session,
    ))
    assert agent_result["success"] is True
    assert db_session.query(AgentLocation).one().agent_id == agent.id

    invalid_driver_result = asyncio.run(main.driver_location_update(
        latitude=42.0,
        longitude=70.0,
        accuracy=None,
        battery=80,
        speed=12,
        token=create_session_token(agent.id, "agent"),
        db=db_session,
    ))
    assert invalid_driver_result == {"success": False, "error": "Invalid token"}
    assert db_session.query(DriverLocation).count() == 0

    driver_result = asyncio.run(main.driver_location_update(
        latitude=42.0,
        longitude=70.0,
        accuracy=None,
        battery=80,
        speed=12,
        token=create_session_token(driver.id, "driver"),
        db=db_session,
    ))
    driver_location = db_session.query(DriverLocation).one()
    assert driver_result["success"] is True
    assert driver_location.driver_id == driver.id
    assert driver_location.speed == 12

    driver_routes = [
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location"
        and "POST" in getattr(route, "methods", set())
    ]
    assert driver_routes[0].endpoint is main.driver_location_update


def test_csrf_middleware_does_not_retry_request_after_failure(monkeypatch):
    async def failing_impl(request, call_next):
        raise RuntimeError("csrf parse failed")

    async def call_next(_request):
        raise AssertionError("request should not be retried after CSRF failure")

    monkeypatch.setattr(main, "_csrf_middleware_impl", failing_impl)

    with pytest.raises(RuntimeError):
        asyncio.run(main.csrf_middleware(object(), call_next))
