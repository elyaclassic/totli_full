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
    Department,
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
    Unit,
    User,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.utils.auth import create_session_token


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _user(db, user_id=1, role="admin", username="admin"):
    user = User(id=user_id, username=username, full_name=username, role=role, is_active=True)
    db.add(user)
    db.flush()
    return user


def _unit(db):
    unit = Unit(code="kg", name="Kilogram")
    db.add(unit)
    db.flush()
    return unit


def _warehouse(db, name, responsible_id=None, department_id=None):
    warehouse = Warehouse(
        code=name.upper(),
        name=name,
        responsible_id=responsible_id,
        department_id=department_id,
        is_active=True,
    )
    db.add(warehouse)
    db.flush()
    return warehouse


def _product(db, code, unit, product_type="material"):
    product = Product(code=code, name=code, type=product_type, unit_id=unit.id, is_active=True)
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_sets_absolute_quantity_and_reverts_delta(db_session):
    user = _user(db_session)
    unit = _unit(db_session)
    warehouse = _warehouse(db_session, "raw")
    product = _product(db_session, "MAT", unit)
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="QLD-1", status="draft", user_id=user.id)
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=15,
        )
    )
    db_session.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user))

    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 15

    main.create_stock_movement(
        db_session,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity_change=3,
        operation_type="purchase",
        document_type="Purchase",
        document_id=999,
    )
    db_session.commit()
    assert stock.quantity == 18

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))

    assert stock.quantity == 13
    revert = db_session.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert revert.quantity_change == -5


def test_production_output_is_not_double_added_and_completion_is_idempotent(db_session):
    user = _user(db_session)
    unit = _unit(db_session)
    raw_wh = _warehouse(db_session, "raw")
    out_wh = _warehouse(db_session, "out")
    material = _product(db_session, "SUGAR", unit)
    finished = _product(db_session, "HALVA", unit, product_type="product")
    recipe = Recipe(product_id=finished.id, name="Halva", output_quantity=5, is_active=True)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=raw_wh.id,
        output_warehouse_id=out_wh.id,
        quantity=1,
        status="draft",
        user_id=user.id,
    )
    db_session.add_all([
        production,
        Stock(warehouse_id=raw_wh.id, product_id=material.id, quantity=10),
    ])
    db_session.commit()

    assert main._do_complete_production_stock(db_session, production, recipe) is None
    production.status = "completed"
    db_session.commit()

    raw_stock = db_session.query(Stock).filter_by(warehouse_id=raw_wh.id, product_id=material.id).one()
    out_stock = db_session.query(Stock).filter_by(warehouse_id=out_wh.id, product_id=finished.id).one()
    assert raw_stock.quantity == 8
    assert out_stock.quantity == 5

    asyncio.run(main.complete_production(production.id, db=db_session, current_user=user))

    assert raw_stock.quantity == 8
    assert out_stock.quantity == 5


def test_signed_mobile_location_routes_bind_active_token_subjects(db_session):
    agent = Agent(id=2, code="AG2", full_name="Agent 2", phone="200", is_active=True)
    driver = Driver(id=3, code="DR3", full_name="Driver 3", phone="300", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()

    assert [route.endpoint.__name__ for route in main.app.routes if getattr(route, "path", None) == "/api/driver/location"][0] == "driver_location_update"

    bad_agent_result = asyncio.run(
        main.agent_location_update(
            latitude=1,
            longitude=2,
            token=create_session_token(agent.id, "user"),
            db=db_session,
        )
    )
    assert bad_agent_result["success"] is False

    agent_result = asyncio.run(
        main.agent_location_update(
            latitude=1,
            longitude=2,
            token=create_session_token(agent.id, "agent"),
            db=db_session,
        )
    )
    assert agent_result["success"] is True
    assert db_session.query(AgentLocation).one().agent_id == agent.id

    driver_result = asyncio.run(
        main.driver_location_update(
            latitude=3,
            longitude=4,
            speed=55,
            token=create_session_token(driver.id, "driver"),
            db=db_session,
        )
    )
    assert driver_result["success"] is True
    location = db_session.query(DriverLocation).one()
    assert location.driver_id == driver.id
    assert location.speed == 55


def test_web_current_user_rejects_mobile_tokens(db_session):
    user = _user(db_session)
    assert get_current_user(session_token=create_session_token(user.id, "agent"), db=db_session) is None
    assert get_current_user(session_token=create_session_token(user.id, "user"), db=db_session).id == user.id


def test_warehouse_transfer_requires_permission_and_replays_once(db_session):
    admin = _user(db_session, user_id=1, role="admin", username="admin")
    stranger = _user(db_session, user_id=2, role="user", username="stranger")
    responsible = _user(db_session, user_id=3, role="user", username="responsible")
    department = Department(code="D1", name="Dept", is_active=True)
    db_session.add(department)
    db_session.flush()
    db_session.add(Employee(code="E1", full_name="Responsible", user_id=responsible.id, department_id=department.id, is_active=True))
    unit = _unit(db_session)
    source = _warehouse(db_session, "source", department_id=department.id)
    dest = _warehouse(db_session, "dest")
    product = _product(db_session, "P1", unit)
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source.id,
        to_warehouse_id=dest.id,
        status="pending_approval",
        user_id=admin.id,
    )
    db_session.add_all([
        transfer,
        Stock(warehouse_id=source.id, product_id=product.id, quantity=10),
    ])
    db_session.flush()
    db_session.add(WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=4))
    db_session.commit()

    with pytest.raises(Exception) as exc:
        asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db_session, current_user=stranger))
    assert getattr(exc.value, "status_code", None) == 403

    asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db_session, current_user=responsible))

    assert transfer.status == "confirmed"
    assert db_session.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one().quantity == 6
    assert db_session.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one().quantity == 4
    assert db_session.query(StockMovement).filter_by(document_type="WarehouseTransfer", document_id=transfer.id).count() == 2

    asyncio.run(main.warehouse_transfer_confirm(transfer.id, db=db_session, current_user=responsible))

    assert db_session.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one().quantity == 6
    assert db_session.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one().quantity == 4
    assert db_session.query(StockMovement).filter_by(document_type="WarehouseTransfer", document_id=transfer.id).count() == 2
