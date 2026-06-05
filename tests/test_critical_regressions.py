import asyncio
from types import SimpleNamespace

import pytest
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
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def _seed_user_warehouse_product(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    warehouse = Warehouse(code="W1", name="Main")
    product = Product(code="P1", name="Product", type="product")
    db.add_all([user, warehouse, product])
    db.commit()
    return user, warehouse, product


def test_stock_adjustment_confirm_and_revert_apply_only_recorded_delta(db_session):
    user, warehouse, product = _seed_user_warehouse_product(db_session)
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.commit()
    item = StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=15,
    )
    db_session.add(item)
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    assert doc.status == "confirmed"
    assert stock.quantity == 15
    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 5
    assert movement.quantity_after == 15

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))

    db_session.refresh(stock)
    db_session.refresh(doc)
    assert doc.status == "draft"
    assert stock.quantity == 10
    reverse = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert reverse.quantity_change == -5
    assert reverse.quantity_after == 10


def test_production_completion_adds_finished_goods_once(db_session):
    user, warehouse, material = _seed_user_warehouse_product(db_session)
    finished = Product(code="FG1", name="Finished", type="product")
    recipe = Recipe(product=finished, name="Recipe", output_quantity=1)
    db_session.add_all([finished, recipe])
    db_session.commit()
    db_session.add_all([
        RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2),
        Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=100),
    ])
    db_session.commit()
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=3,
        status="draft",
        user_id=user.id,
    )
    db_session.add(production)
    db_session.commit()

    response = main._do_complete_production_stock(db_session, production, recipe)
    db_session.commit()

    assert response is None
    material_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=material.id,
    ).one()
    finished_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=finished.id,
    ).one()
    assert material_stock.quantity == 94
    assert finished_stock.quantity == 3
    output_movement = db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert output_movement.quantity_change == 3
    assert output_movement.quantity_after == 3


def test_pwa_location_requires_expected_signed_token_type(db_session):
    agent = Agent(code="A1", full_name="Agent One", phone="1", is_active=True)
    driver = Driver(code="D1", full_name="Driver One", phone="2", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()

    bad_agent_response = asyncio.run(main.agent_location_update(
        latitude=41.0,
        longitude=69.0,
        accuracy=None,
        battery=None,
        token="not-a-token",
        db=db_session,
    ))
    assert bad_agent_response == {"success": False, "error": "Invalid token"}
    assert db_session.query(AgentLocation).count() == 0

    agent_response = asyncio.run(main.agent_location_update(
        latitude=41.0,
        longitude=69.0,
        accuracy=None,
        battery=None,
        token=create_session_token(agent.id, "agent"),
        db=db_session,
    ))
    assert agent_response["success"] is True
    assert db_session.query(AgentLocation).one().agent_id == agent.id

    wrong_driver_response = asyncio.run(main.driver_location_update(
        latitude=41.0,
        longitude=69.0,
        accuracy=None,
        battery=None,
        token=create_session_token(agent.id, "agent"),
        db=db_session,
    ))
    assert wrong_driver_response == {"success": False, "error": "Invalid token"}
    assert db_session.query(DriverLocation).count() == 0

    driver_response = asyncio.run(main.driver_location_update(
        latitude=41.0,
        longitude=69.0,
        accuracy=None,
        battery=None,
        token=create_session_token(driver.id, "driver"),
        db=db_session,
    ))
    assert driver_response["success"] is True
    assert db_session.query(DriverLocation).one().driver_id == driver.id


def test_only_token_protected_driver_location_route_is_registered():
    active_routes = [
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location"
        and "POST" in getattr(route, "methods", set())
    ]
    assert len(active_routes) == 1
    assert active_routes[0].endpoint is main.driver_location_update


def test_csrf_middleware_does_not_retry_request_after_exception(monkeypatch):
    async def boom(request, call_next):
        raise RuntimeError("csrf parsing failed")

    called = False

    async def call_next(request):
        nonlocal called
        called = True
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr(main, "_csrf_middleware_impl", boom)

    with pytest.raises(RuntimeError, match="csrf parsing failed"):
        asyncio.run(main.csrf_middleware(SimpleNamespace(method="POST"), call_next))
    assert called is False
