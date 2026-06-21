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
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _user(db, role="admin"):
    user = User(username=f"{role}_user", full_name="Test User", role=role, is_active=True)
    db.add(user)
    db.flush()
    return user


def _warehouse(db):
    warehouse = Warehouse(code="W1", name="Main warehouse", is_active=True)
    db.add(warehouse)
    db.flush()
    return warehouse


def _product(db, code, name, product_type="product", purchase_price=0):
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


def test_stock_adjustment_confirm_and_revert_do_not_double_apply(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session, "P1", "Product")
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add(doc)
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

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db_session, user))

    stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 150
    movement = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 50
    assert movement.quantity_after == 150

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db_session, user))

    db_session.refresh(stock)
    assert stock.quantity == 100
    revert = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert revert.quantity_change == -50
    assert revert.quantity_after == 100


def test_production_completion_adds_output_once(db_session):
    user = _user(db_session)
    warehouse = _warehouse(db_session)
    raw = _product(db_session, "RAW", "Raw material", product_type="material", purchase_price=2)
    output = _product(db_session, "OUT", "Finished product", purchase_price=5)
    db_session.add_all(
        [
            Stock(warehouse_id=warehouse.id, product_id=raw.id, quantity=100),
            Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=5),
        ]
    )
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=1, is_active=True)
    db_session.add(recipe)
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
    raw_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw.id).one()
    output_stock = db_session.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
    assert raw_stock.quantity == 90
    assert output_stock.quantity == 15
    output_movement = db_session.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert output_movement.quantity_change == 10
    assert output_movement.quantity_after == 15


def test_mobile_tokens_cannot_be_used_as_web_sessions(db_session):
    web_user = _user(db_session, role="admin")
    agent = Agent(code="AG1", full_name="Agent One", phone="100", is_active=True)
    db_session.add(agent)
    db_session.flush()
    assert agent.id == web_user.id
    db_session.commit()

    agent_token = create_session_token(agent.id, "agent")

    assert get_current_user(session_token=agent_token, db=db_session) is None


def test_agent_location_requires_agent_token_and_uses_token_subject(db_session):
    agent = Agent(code="AG1", full_name="Agent One", phone="100", is_active=True)
    driver = Driver(code="DR1", full_name="Driver One", phone="200", is_active=True)
    db_session.add_all([agent, driver])
    db_session.commit()

    driver_token = create_session_token(driver.id, "driver")
    assert asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            token=driver_token,
            db=db_session,
        )
    ) == {"success": False, "error": "Invalid token"}

    agent_token = create_session_token(agent.id, "agent")
    result = asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            token=agent_token,
            db=db_session,
        )
    )

    assert result["success"] is True
    location = db_session.query(AgentLocation).one()
    assert location.agent_id == agent.id
