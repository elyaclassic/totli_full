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
    Partner,
    Product,
    Production,
    ProductionItem,
    Recipe,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    User,
    Warehouse,
)
from app.utils.auth import create_session_token


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def seed_user_warehouse_product(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    warehouse = Warehouse(code="W1", name="Main")
    product = Product(code="P1", name="Product", type="product", purchase_price=10, sale_price=20, is_active=True)
    db.add_all([user, warehouse, product])
    db.commit()
    return user, warehouse, product


def test_stock_adjustment_confirm_applies_absolute_quantity_once():
    db = make_session()
    try:
        user, warehouse, product = seed_user_warehouse_product(db)
        stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
        doc = StockAdjustmentDoc(number="SA-1", status="draft", user_id=user.id)
        db.add_all([stock, doc])
        db.flush()
        db.add(StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=25,
            cost_price=10,
            sale_price=20,
        ))
        db.commit()

        asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))

        db.refresh(stock)
        movement = db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment",
        ).one()
        assert stock.quantity == 25
        assert movement.quantity_change == 15
        assert movement.quantity_after == 25
    finally:
        db.close()


def test_stock_adjustment_revert_uses_inverse_movement():
    db = make_session()
    try:
        user, warehouse, product = seed_user_warehouse_product(db)
        stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
        doc = StockAdjustmentDoc(number="SA-2", status="draft", user_id=user.id)
        db.add_all([stock, doc])
        db.flush()
        db.add(StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=25,
        ))
        db.commit()

        asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))
        asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db, user))

        db.refresh(stock)
        db.refresh(doc)
        revert = db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment_revert",
        ).one()
        assert stock.quantity == 10
        assert doc.status == "draft"
        assert revert.quantity_change == -15
        assert revert.quantity_after == 10
    finally:
        db.close()


def test_production_completion_adds_output_once():
    db = make_session()
    try:
        user, warehouse, output = seed_user_warehouse_product(db)
        material = Product(code="M1", name="Material", type="material", purchase_price=3, is_active=True)
        recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=2, is_active=True)
        db.add_all([material, recipe])
        db.flush()
        production = Production(
            number="PR-1",
            recipe_id=recipe.id,
            warehouse_id=warehouse.id,
            quantity=4,
            status="draft",
            user_id=user.id,
        )
        db.add(production)
        db.flush()
        db.add_all([
            ProductionItem(production_id=production.id, product_id=material.id, quantity=10),
            Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=100),
            Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=5),
        ])
        db.commit()

        err = main._do_complete_production_stock(db, production, recipe)
        db.commit()

        material_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
        output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
        assert err is None
        assert material_stock.quantity == 90
        assert output_stock.quantity == 13
    finally:
        db.close()


def test_complete_production_is_noop_when_already_completed():
    db = make_session()
    try:
        user, warehouse, output = seed_user_warehouse_product(db)
        recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=1, is_active=True)
        db.add(recipe)
        db.flush()
        production = Production(
            number="PR-2",
            recipe_id=recipe.id,
            warehouse_id=warehouse.id,
            quantity=5,
            status="completed",
            user_id=user.id,
        )
        output_stock = Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=7)
        db.add_all([production, output_stock])
        db.commit()

        response = asyncio.run(main.complete_production(production.id, db, user))

        db.refresh(output_stock)
        assert response.status_code == 303
        assert output_stock.quantity == 7
        assert db.query(StockMovement).count() == 0
    finally:
        db.close()


def test_agent_location_rejects_cross_type_token_and_uses_token_subject():
    db = make_session()
    try:
        agent = Agent(code="A1", full_name="Agent One", phone="+100", is_active=True)
        other_agent = Agent(code="A2", full_name="Agent Two", phone="+200", is_active=True)
        driver = Driver(code="D1", full_name="Driver One", phone="+300", is_active=True)
        db.add_all([agent, other_agent, driver])
        db.commit()

        driver_token = create_session_token(driver.id, "driver")
        bad = asyncio.run(main.agent_location_update(41.0, 69.0, None, None, driver_token, db))
        assert bad == {"success": False, "error": "Invalid token"}
        assert db.query(AgentLocation).count() == 0

        agent_token = create_session_token(other_agent.id, "agent")
        good = asyncio.run(main.agent_location_update(41.1, 69.1, 5, 80, agent_token, db))
        location = db.query(AgentLocation).one()
        assert good["success"] is True
        assert location.agent_id == other_agent.id
    finally:
        db.close()


def test_driver_location_live_route_uses_signed_token_handler():
    matches = [
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location" and "POST" in getattr(route, "methods", set())
    ]
    assert matches
    assert matches[0].endpoint.__name__ == "driver_location_update"


def test_driver_location_rejects_agent_token():
    db = make_session()
    try:
        agent = Agent(code="A1", full_name="Agent One", phone="+100", is_active=True)
        driver = Driver(code="D1", full_name="Driver One", phone="+300", is_active=True)
        db.add_all([agent, driver])
        db.commit()

        agent_token = create_session_token(agent.id, "agent")
        response = asyncio.run(main.driver_location_update(41.0, 69.0, None, None, agent_token, db))
        assert response == {"success": False, "error": "Invalid token"}
        assert db.query(DriverLocation).count() == 0
    finally:
        db.close()


def test_agent_partners_requires_agent_token_and_web_deps_reject_mobile_token():
    db = make_session()
    try:
        user = User(username="web", password_hash="x", full_name="Web", role="user", is_active=True)
        driver = Driver(code="D1", full_name="Driver One", phone="+300", is_active=True)
        partner = Partner(code="P1", name="Customer", type="customer", phone="+400", is_active=True)
        db.add_all([user, driver, partner])
        db.commit()

        driver_token = create_session_token(driver.id, "driver")
        response = asyncio.run(main.agent_partners(driver_token, db))
        assert response == {"success": False, "error": "Invalid token"}
        assert get_current_user(session_token=driver_token, db=db) is None
    finally:
        db.close()
