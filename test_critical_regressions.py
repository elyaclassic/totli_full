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
        engine.dispose()


def _user(db, username="admin", role="admin"):
    user = User(
        username=username,
        password_hash="x",
        full_name=username.title(),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _warehouse(db, code="WH", **kwargs):
    warehouse = Warehouse(code=code, name=code, is_active=True, **kwargs)
    db.add(warehouse)
    db.flush()
    return warehouse


def _product(db, code="P", name="Product", product_type="product", purchase_price=0):
    product = Product(
        code=code,
        name=name,
        type=product_type,
        purchase_price=purchase_price,
        is_active=True,
    )
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirm_and_revert_use_recorded_delta_once(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session)
    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100)
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add_all([stock, doc])
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=150,
        )
    )
    db_session.commit()

    response = asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    assert response.status_code == 303
    db_session.refresh(stock)
    assert stock.quantity == 150
    movement = db_session.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert movement.quantity_change == 50
    assert movement.quantity_after == 150

    response = asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    assert response.status_code == 303
    db_session.refresh(stock)
    assert stock.quantity == 100
    revert = db_session.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert.quantity_change == -50
    assert revert.quantity_after == 100


def test_production_completion_adds_finished_goods_once(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    raw = _product(db_session, "RAW", "Raw material", product_type="material", purchase_price=2)
    output = _product(db_session, "OUT", "Finished product", purchase_price=5)
    raw_stock = Stock(warehouse_id=warehouse.id, product_id=raw.id, quantity=100)
    output_stock = Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=5)
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=1, is_active=True)
    db_session.add_all([raw_stock, output_stock, recipe])
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=1))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=10,
        status="draft",
        user_id=user.id,
    )
    db_session.add(production)
    db_session.commit()

    error_response = main._do_complete_production_stock(db_session, production, recipe)

    assert error_response is None
    db_session.flush()
    db_session.refresh(raw_stock)
    db_session.refresh(output_stock)
    assert raw_stock.quantity == 90
    assert output_stock.quantity == 15
    output_movement = db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert output_movement.quantity_change == 10
    assert output_movement.quantity_after == 15


def test_completed_production_cannot_be_cancelled_or_deleted_before_revert(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    output = _product(db_session, "OUT", "Finished product")
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=1, is_active=True)
    production = Production(
        number="PR-DONE",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=3,
        status="completed",
        user_id=user.id,
    )
    db_session.add_all([recipe, production])
    db_session.commit()

    response = asyncio.run(main.cancel_production(production.id, db_session, user))

    assert response.status_code == 303
    db_session.refresh(production)
    assert production.status == "completed"

    response = asyncio.run(main.delete_production(production.id, db_session, user))

    assert response.status_code == 303
    assert db_session.query(Production).filter_by(id=production.id).one().status == "completed"


def test_mobile_tokens_cannot_authenticate_as_web_sessions(db_session):
    web_user = _user(db_session, username="web", role="admin")
    agent = Agent(code="AG1", full_name="Agent One", phone="100", is_active=True)
    db_session.add(agent)
    db_session.flush()
    assert agent.id == web_user.id

    agent_token = create_session_token(agent.id, "agent")
    web_token = create_session_token(web_user.id, "user")

    assert get_current_user(session_token=agent_token, db=db_session) is None
    assert get_current_user(session_token=web_token, db=db_session).id == web_user.id


def test_location_updates_require_matching_active_mobile_token(db_session):
    agent = Agent(code="AG1", full_name="Agent One", phone="100", is_active=True)
    driver = Driver(code="DR1", full_name="Driver One", phone="200", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()

    driver_token = create_session_token(driver.id, "driver")
    assert asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            accuracy=None,
            battery=None,
            token=driver_token,
            db=db_session,
        )
    ) == {"success": False, "error": "Invalid token"}

    agent_token = create_session_token(agent.id, "agent")
    result = asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            accuracy=None,
            battery=None,
            token=agent_token,
            db=db_session,
        )
    )

    assert result["success"] is True
    location = db_session.query(AgentLocation).one()
    assert location.agent_id == agent.id

    driver_result = asyncio.run(
        main.driver_location_update(
            latitude=42.0,
            longitude=70.0,
            accuracy=None,
            battery=None,
            speed=25.5,
            token=driver_token,
            db=db_session,
        )
    )
    assert driver_result["success"] is True
    driver_location = db_session.query(DriverLocation).one()
    assert driver_location.driver_id == driver.id
    assert driver_location.speed == 25.5


def test_only_token_driver_location_route_is_active():
    routes = [
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location"
    ]

    assert len(routes) == 1
    assert routes[0].endpoint is main.driver_location_update


def test_warehouse_transfer_confirm_requires_permission_and_is_idempotent(db_session):
    admin = _user(db_session, username="admin", role="admin")
    ordinary = _user(db_session, username="ordinary", role="user")
    source = _warehouse(db_session, "SRC")
    dest = _warehouse(db_session, "DST")
    product = _product(db_session)
    source_stock = Stock(warehouse_id=source.id, product_id=product.id, quantity=20)
    transfer = WarehouseTransfer(
        number="WT-1",
        from_warehouse_id=source.id,
        to_warehouse_id=dest.id,
        status="pending_approval",
        user_id=ordinary.id,
    )
    db_session.add_all([source_stock, transfer])
    db_session.flush()
    db_session.add(WarehouseTransferItem(
        transfer_id=transfer.id,
        product_id=product.id,
        quantity=5,
    ))
    db_session.commit()

    response = asyncio.run(main.warehouse_transfer_confirm(transfer.id, db_session, ordinary))

    assert response.status_code == 303
    db_session.refresh(source_stock)
    db_session.refresh(transfer)
    assert source_stock.quantity == 20
    assert transfer.status == "pending_approval"
    assert db_session.query(StockMovement).count() == 0

    response = asyncio.run(main.warehouse_transfer_confirm(transfer.id, db_session, admin))

    assert response.status_code == 303
    db_session.refresh(source_stock)
    db_session.refresh(transfer)
    dest_stock = db_session.query(Stock).filter_by(
        warehouse_id=dest.id,
        product_id=product.id,
    ).one()
    assert source_stock.quantity == 15
    assert dest_stock.quantity == 5
    assert transfer.status == "confirmed"
    assert db_session.query(StockMovement).count() == 2

    response = asyncio.run(main.warehouse_transfer_confirm(transfer.id, db_session, admin))

    assert response.status_code == 303
    db_session.refresh(source_stock)
    db_session.refresh(dest_stock)
    assert source_stock.quantity == 15
    assert dest_stock.quantity == 5
    assert db_session.query(StockMovement).count() == 2
