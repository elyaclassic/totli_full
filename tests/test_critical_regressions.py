import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main as app_main
from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Category,
    Driver,
    Product,
    Production,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    Unit,
    User,
    Warehouse,
)
from app.utils.auth import create_session_token, get_user_from_token


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
        Base.metadata.drop_all(bind=engine)


def _user(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    db.add(user)
    db.commit()
    return user


def _product_setup(db):
    category = Category(code="CAT", name="Category", type="material")
    unit = Unit(code="kg", name="Kilogram")
    warehouse = Warehouse(code="WH", name="Warehouse")
    product = Product(code="P1", name="Product", type="product", category=category, unit=unit)
    db.add_all([category, unit, warehouse, product])
    db.commit()
    return warehouse, product


def test_stock_adjustment_confirm_and_revert_apply_delta_once(db_session):
    user = _user(db_session)
    warehouse, product = _product_setup(db_session)
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.commit()
    item = StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=25,
    )
    db_session.add(item)
    db_session.commit()

    asyncio.run(app_main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    db_session.refresh(stock)
    assert stock.quantity == 25
    movement = db_session.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert movement.quantity_change == 15
    assert movement.quantity_after == 25

    asyncio.run(app_main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    db_session.refresh(stock)
    assert stock.quantity == 10
    revert = db_session.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert.quantity_change == -15
    assert revert.quantity_after == 10


def test_production_completion_adds_finished_goods_once(db_session):
    user = _user(db_session)
    input_wh, raw_product = _product_setup(db_session)
    output_product = Product(code="OUT", name="Output", type="product", unit_id=raw_product.unit_id)
    db_session.add(output_product)
    db_session.commit()
    recipe = Recipe(product_id=output_product.id, name="Recipe", output_quantity=2)
    db_session.add(recipe)
    db_session.commit()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=3))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=input_wh.id,
        output_warehouse_id=input_wh.id,
        quantity=4,
        user_id=user.id,
    )
    db_session.add_all([
        Stock(warehouse_id=input_wh.id, product_id=raw_product.id, quantity=100),
        Stock(warehouse_id=input_wh.id, product_id=output_product.id, quantity=5),
        production,
    ])
    db_session.commit()

    result = app_main._do_complete_production_stock(db_session, production, recipe)
    db_session.commit()

    assert result is None
    output_stock = db_session.query(Stock).filter_by(
        warehouse_id=input_wh.id,
        product_id=output_product.id,
    ).one()
    raw_stock = db_session.query(Stock).filter_by(
        warehouse_id=input_wh.id,
        product_id=raw_product.id,
    ).one()
    assert output_stock.quantity == 13
    assert raw_stock.quantity == 88


def test_agent_location_uses_token_agent_and_rejects_web_token(db_session):
    user = _user(db_session)
    first_agent = Agent(code="A1", full_name="First", phone="111", is_active=True)
    second_agent = Agent(code="A2", full_name="Second", phone="222", is_active=True)
    db_session.add_all([first_agent, second_agent])
    db_session.commit()

    web_token = create_session_token(user.id, user.username)
    rejected = asyncio.run(app_main.agent_location_update(1.0, 2.0, None, None, web_token, db_session))
    assert rejected == {"success": False, "error": "Invalid token"}

    agent_token = create_session_token(second_agent.id, "agent")
    accepted = asyncio.run(app_main.agent_location_update(1.0, 2.0, None, 90, agent_token, db_session))
    assert accepted["success"] is True
    location = db_session.query(AgentLocation).one()
    assert location.agent_id == second_agent.id


def test_pwa_login_tokens_and_driver_location_route_are_bound_to_mobile_type(db_session):
    agent = Agent(code="A1", full_name="Agent", phone="111", is_active=True)
    driver = Driver(code="D1", full_name="Driver", phone="222", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()

    login = asyncio.run(app_main.agent_login("111", "111", db_session))
    assert login["success"] is True
    assert get_user_from_token(login["token"])["user_type"] == "agent"

    driver_routes = [
        route
        for route in app_main.app.routes
        if getattr(route, "path", None) == "/api/driver/location"
        and "POST" in getattr(route, "methods", set())
    ]
    assert [route.endpoint.__name__ for route in driver_routes] == ["driver_location_update"]
