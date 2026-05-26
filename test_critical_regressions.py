import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
    Agent,
    AgentLocation,
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
    Warehouse,
)
from app.utils.auth import create_session_token, get_user_from_token


class DummyUser:
    id = 1


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSession()


def test_stock_adjustment_confirm_and_revert_apply_single_delta():
    db = make_session()
    warehouse = Warehouse(code="W1", name="Warehouse")
    product = Product(code="P1", name="Product", type="product")
    db.add_all([warehouse, product])
    db.flush()

    stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
    doc = StockAdjustmentDoc(number="ADJ-1", status="draft")
    db.add_all([stock, doc])
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
        )
    )
    db.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=DummyUser()))
    db.refresh(stock)

    assert stock.quantity == 50
    movement = db.query(StockMovement).filter_by(document_type="StockAdjustmentDoc", document_id=doc.id).one()
    assert movement.quantity_change == 40
    assert movement.quantity_after == 50

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=DummyUser()))
    db.refresh(stock)

    assert stock.quantity == 10


def test_production_completion_posts_finished_goods_once_and_is_idempotent():
    db = make_session()
    warehouse = Warehouse(code="W1", name="Warehouse")
    material = Product(code="M1", name="Material", type="material", purchase_price=2)
    output = Product(code="P1", name="Output", type="product")
    db.add_all([warehouse, material, output])
    db.flush()

    db.add_all(
        [
            Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=100),
            Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=5),
        ]
    )
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=3)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=4))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=2,
        status="draft",
        user_id=DummyUser.id,
    )
    db.add(production)
    db.commit()

    err = main._do_complete_production_stock(db, production, recipe)
    assert err is None
    production.status = "completed"
    db.commit()

    material_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
    output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
    assert material_stock.quantity == 92
    assert output_stock.quantity == 11

    response = asyncio.run(main.complete_production(production.id, db=db, current_user=DummyUser()))
    assert response.status_code == 303
    db.refresh(material_stock)
    db.refresh(output_stock)
    assert material_stock.quantity == 92
    assert output_stock.quantity == 11


def test_pwa_tokens_login_and_location_use_signed_user_type():
    db = make_session()
    agent = Agent(code="A1", full_name="Agent One", phone="111", is_active=True)
    driver = Driver(code="D1", full_name="Driver One", phone="222", vehicle_number="01A", is_active=True)
    db.add_all([agent, driver])
    db.commit()

    agent_login = asyncio.run(main.agent_login(username="111", password="111", db=db))
    driver_login = asyncio.run(main.driver_login(username="222", password="222", db=db))

    assert get_user_from_token(agent_login["token"])["user_type"] == "agent"
    assert get_user_from_token(driver_login["token"])["user_type"] == "driver"

    wrong_type = create_session_token(driver.id, "driver")
    rejected = asyncio.run(
        main.agent_location_update(latitude=41.0, longitude=69.0, accuracy=5, battery=90, token=wrong_type, db=db)
    )
    assert rejected == {"success": False, "error": "Invalid token"}

    saved_agent = asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            accuracy=5,
            battery=90,
            token=agent_login["token"],
            db=db,
        )
    )
    saved_driver = asyncio.run(
        main.driver_location_update(
            latitude=42.0,
            longitude=70.0,
            accuracy=6,
            battery=80,
            token=driver_login["token"],
            db=db,
        )
    )

    assert saved_agent["success"] is True
    assert saved_driver["success"] is True
    assert db.query(AgentLocation).one().agent_id == agent.id
    assert db.query(DriverLocation).one().driver_id == driver.id


def test_driver_token_location_route_is_not_shadowed_by_legacy_code_route():
    routes = [
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location" and "POST" in getattr(route, "methods", set())
    ]

    assert len(routes) == 1
    assert routes[0].endpoint is main.driver_location_update
