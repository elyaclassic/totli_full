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
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _user(db_session, username="admin", role="admin"):
    user = User(username=username, password_hash="x", full_name=username, role=role, is_active=True)
    db_session.add(user)
    db_session.commit()
    return user


def _warehouse(db_session, code="W1"):
    warehouse = Warehouse(code=code, name=code, is_active=True)
    db_session.add(warehouse)
    db_session.commit()
    return warehouse


def _product(db_session, code="P1", name="Product", product_type="product"):
    product = Product(code=code, name=name, type=product_type, is_active=True, purchase_price=10)
    db_session.add(product)
    db_session.commit()
    return product


def test_stock_adjustment_confirm_and_revert_apply_recorded_delta_once(db_session):
    admin = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session)
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=admin.id, status="draft")
    db_session.add(doc)
    db_session.commit()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=25,
        )
    )
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, admin))

    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == pytest.approx(25)
    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == pytest.approx(15)
    assert movement.quantity_after == pytest.approx(25)

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, admin))

    db_session.refresh(stock)
    assert stock.quantity == pytest.approx(10)
    revert = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert revert.quantity_change == pytest.approx(-15)
    assert revert.quantity_after == pytest.approx(10)

    # A second confirm/revert cycle must only invert the latest confirmation movements.
    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, admin))
    db_session.refresh(stock)
    assert stock.quantity == pytest.approx(25)
    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, admin))
    db_session.refresh(stock)
    assert stock.quantity == pytest.approx(10)


def test_production_complete_is_single_apply_and_idempotent(db_session):
    admin = _user(db_session)
    raw_wh = _warehouse(db_session, "RAW")
    out_wh = _warehouse(db_session, "OUT")
    raw = _product(db_session, "RAW-P", "Raw", "material")
    finished = _product(db_session, "FIN-P", "Finished", "product")
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1, is_active=True)
    db_session.add(recipe)
    db_session.commit()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=1))
    production = Production(
        number="PROD-1",
        recipe_id=recipe.id,
        warehouse_id=raw_wh.id,
        output_warehouse_id=out_wh.id,
        quantity=5,
        status="draft",
        user_id=admin.id,
    )
    db_session.add_all(
        [
            Stock(warehouse_id=raw_wh.id, product_id=raw.id, quantity=20),
            Stock(warehouse_id=out_wh.id, product_id=finished.id, quantity=10),
            production,
        ]
    )
    db_session.commit()

    asyncio.run(main.complete_production(production.id, db_session, admin))

    raw_stock = db_session.query(Stock).filter_by(warehouse_id=raw_wh.id, product_id=raw.id).one()
    finished_stock = db_session.query(Stock).filter_by(warehouse_id=out_wh.id, product_id=finished.id).one()
    db_session.refresh(production)
    assert production.status == "completed"
    assert raw_stock.quantity == pytest.approx(15)
    assert finished_stock.quantity == pytest.approx(15)
    assert db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).count() == 1

    asyncio.run(main.complete_production(production.id, db_session, admin))

    db_session.refresh(raw_stock)
    db_session.refresh(finished_stock)
    assert raw_stock.quantity == pytest.approx(15)
    assert finished_stock.quantity == pytest.approx(15)
    assert db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).count() == 1

    asyncio.run(main.delete_production(production.id, db_session, admin))
    assert db_session.query(Production).filter_by(id=production.id).one().status == "completed"


def test_mobile_location_routes_validate_signed_active_subject_tokens(db_session):
    admin = _user(db_session)
    agent = Agent(code="A1", full_name="Agent One", phone="100", is_active=True)
    driver = Driver(code="D1", full_name="Driver One", phone="200", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()

    driver_route = next(
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location" and "POST" in getattr(route, "methods", set())
    )
    assert driver_route.endpoint.__name__ == "driver_location_update"

    web_token = create_session_token(admin.id, "user")
    agent_token = create_session_token(agent.id, "agent")
    driver_token = create_session_token(driver.id, "driver")

    assert get_current_user(session_token=agent_token, db=db_session) is None
    assert get_current_user(session_token=driver_token, db=db_session) is None
    assert get_current_user(session_token=web_token, db=db_session).id == admin.id

    assert asyncio.run(
        main.agent_location_update(41.0, 69.0, accuracy=5, battery=80, token=web_token, db=db_session)
    )["success"] is False
    assert db_session.query(AgentLocation).count() == 0

    result = asyncio.run(
        main.agent_location_update(41.0, 69.0, accuracy=5, battery=80, token=agent_token, db=db_session)
    )
    assert result["success"] is True
    assert db_session.query(AgentLocation).one().agent_id == agent.id

    result = asyncio.run(
        main.driver_location_update(40.0, 68.0, accuracy=7, battery=70, speed=42, token=driver_token, db=db_session)
    )
    assert result["success"] is True
    driver_location = db_session.query(DriverLocation).one()
    assert driver_location.driver_id == driver.id
    assert driver_location.speed == pytest.approx(42)
