import asyncio

import pytest
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
    Partner,
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
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _user(db, *, role="admin"):
    user = User(username=f"{role}_user", password_hash="x", full_name="User", role=role, is_active=True)
    db.add(user)
    db.flush()
    return user


def _warehouse(db, code):
    warehouse = Warehouse(code=code, name=code, is_active=True)
    db.add(warehouse)
    db.flush()
    return warehouse


def _product(db, code, *, product_type="product", purchase_price=0):
    product = Product(code=code, name=code, type=product_type, purchase_price=purchase_price, is_active=True)
    db.add(product)
    db.flush()
    return product


def test_stock_adjustment_confirm_applies_delta_once_and_revert_restores_previous(db_session):
    db = db_session
    user = _user(db)
    warehouse = _warehouse(db, "WH")
    product = _product(db, "P")
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db.add(doc)
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

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    movement = db.query(StockMovement).filter_by(document_type="StockAdjustmentDoc", document_id=doc.id).one()
    assert stock.quantity == 50
    assert movement.quantity_change == 40
    assert movement.quantity_after == 50

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))

    db.refresh(stock)
    db.refresh(doc)
    assert stock.quantity == 10
    assert doc.status == "draft"


def test_production_complete_adds_finished_goods_once_and_is_idempotent(db_session, monkeypatch):
    db = db_session
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    user = _user(db)
    raw_warehouse = _warehouse(db, "RAW")
    output_warehouse = _warehouse(db, "OUT")
    material = _product(db, "RAW-P", product_type="material", purchase_price=2)
    finished = _product(db, "FIN-P", purchase_price=10)
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1, is_active=True)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PROD-1",
        recipe_id=recipe.id,
        warehouse_id=raw_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=10,
        status="draft",
        user_id=user.id,
    )
    db.add_all(
        [
            Stock(warehouse_id=raw_warehouse.id, product_id=material.id, quantity=100),
            Stock(warehouse_id=output_warehouse.id, product_id=finished.id, quantity=5),
            production,
        ]
    )
    db.commit()

    asyncio.run(main.complete_production(production.id, db=db, current_user=user))

    raw_stock = db.query(Stock).filter_by(warehouse_id=raw_warehouse.id, product_id=material.id).one()
    finished_stock = db.query(Stock).filter_by(warehouse_id=output_warehouse.id, product_id=finished.id).one()
    assert raw_stock.quantity == 80
    assert finished_stock.quantity == 15

    asyncio.run(main.complete_production(production.id, db=db, current_user=user))

    db.refresh(raw_stock)
    db.refresh(finished_stock)
    assert raw_stock.quantity == 80
    assert finished_stock.quantity == 15


def test_transfer_revert_does_not_create_inventory_when_destination_is_short(db_session):
    db = db_session
    user = _user(db)
    source = _warehouse(db, "SRC")
    dest = _warehouse(db, "DST")
    product = _product(db, "P")
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source.id,
        to_warehouse_id=dest.id,
        status="confirmed",
        user_id=user.id,
    )
    db.add(transfer)
    db.flush()
    db.add_all(
        [
            WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=100),
            Stock(warehouse_id=source.id, product_id=product.id, quantity=0),
            Stock(warehouse_id=dest.id, product_id=product.id, quantity=20),
        ]
    )
    db.commit()

    response = asyncio.run(main.warehouse_transfer_revert(transfer.id, db=db, current_user=user))

    source_stock = db.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one()
    dest_stock = db.query(Stock).filter_by(warehouse_id=dest.id, product_id=product.id).one()
    db.refresh(transfer)
    assert response.status_code == 303
    assert "error=" in response.headers["location"]
    assert source_stock.quantity == 0
    assert dest_stock.quantity == 20
    assert transfer.status == "confirmed"


def test_mobile_tokens_do_not_authenticate_as_web_users(db_session):
    db = db_session
    user = _user(db)
    db.add(Agent(id=user.id, code="A1", full_name="Agent", phone="100", is_active=True))
    db.commit()

    assert get_current_user(create_session_token(user.id, "agent"), db) is None
    assert get_current_user(create_session_token(user.id, "driver"), db) is None
    assert get_current_user(create_session_token(user.id, "user"), db).id == user.id


def test_agent_location_requires_agent_token_and_uses_token_subject(db_session):
    db = db_session
    db.add(Agent(id=7, code="A7", full_name="Agent 7", phone="700", is_active=True))
    db.commit()

    invalid = asyncio.run(
        main.agent_location_update(latitude=1, longitude=2, accuracy=3, battery=90, token="bad", db=db)
    )
    assert invalid["success"] is False
    assert db.query(AgentLocation).count() == 0

    token = create_session_token(7, "agent")
    valid = asyncio.run(
        main.agent_location_update(latitude=1, longitude=2, accuracy=3, battery=90, token=token, db=db)
    )

    location = db.query(AgentLocation).one()
    assert valid["success"] is True
    assert location.agent_id == 7


def test_agent_partners_requires_agent_token_and_scopes_to_agent(db_session):
    db = db_session
    db.add_all(
        [
            Agent(id=7, code="A7", full_name="Agent 7", phone="700", is_active=True),
            Agent(id=8, code="A8", full_name="Agent 8", phone="800", is_active=True),
            Partner(code="P7", name="Own", type="customer", phone="1", address="A", agent_id=7, is_active=True),
            Partner(code="P8", name="Other", type="customer", phone="2", address="B", agent_id=8, is_active=True),
        ]
    )
    db.commit()

    invalid = asyncio.run(main.agent_partners(token=create_session_token(7, "driver"), db=db))
    valid = asyncio.run(main.agent_partners(token=create_session_token(7, "agent"), db=db))

    assert invalid["success"] is False
    assert valid["success"] is True
    assert [partner["name"] for partner in valid["partners"]] == ["Own"]
