import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
    Product,
    Purchase,
    PurchaseItem,
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
    Production,
)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def user(db):
    user = User(username="admin", full_name="Admin", role="admin", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_product(db, code, name):
    product = Product(code=code, name=name, type="product", is_active=True, min_stock=0)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_warehouse(db, code, name):
    warehouse = Warehouse(code=code, name=name, is_active=True)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def stock_quantity(db, warehouse_id, product_id):
    stock = db.query(Stock).filter(
        Stock.warehouse_id == warehouse_id,
        Stock.product_id == product_id,
    ).first()
    return stock.quantity if stock else None


def test_stock_adjustment_confirm_sets_target_once_and_revert_restores_delta(db, user):
    warehouse = add_warehouse(db, "W1", "Main")
    product = add_product(db, "P1", "Halva")
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="ADJ-1", status="draft", user_id=user.id)
    db.add(doc)
    db.commit()
    db.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=15,
    ))
    db.commit()

    run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))

    assert stock_quantity(db, warehouse.id, product.id) == 15
    movement = db.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 5
    assert movement.quantity_after == 15

    run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db, user))

    assert stock_quantity(db, warehouse.id, product.id) == 10
    revert = db.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert revert.quantity_change == -5
    assert db.query(StockAdjustmentDoc).get(doc.id).status == "draft"


def test_production_complete_adds_output_once_and_is_idempotent(db, user, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: 0)
    warehouse = add_warehouse(db, "W1", "Main")
    raw = add_product(db, "RAW", "Sugar")
    output = add_product(db, "OUT", "Finished")
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=2, is_active=True)
    db.add(recipe)
    db.commit()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=raw.id, quantity=1))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=2,
        status="draft",
        user_id=user.id,
    )
    db.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw.id, quantity=10),
        Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=3),
        production,
    ])
    db.commit()
    db.refresh(production)

    run(main.complete_production(production.id, db, user))

    assert stock_quantity(db, warehouse.id, raw.id) == 8
    assert stock_quantity(db, warehouse.id, output.id) == 7
    assert db.query(Production).get(production.id).status == "completed"

    run(main.complete_production(production.id, db, user))

    assert stock_quantity(db, warehouse.id, raw.id) == 8
    assert stock_quantity(db, warehouse.id, output.id) == 7
    assert db.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).count() == 1


def test_transfer_revert_rejects_when_destination_stock_was_consumed(db, user):
    source = add_warehouse(db, "SRC", "Source")
    dest = add_warehouse(db, "DST", "Destination")
    product = add_product(db, "P1", "Halva")
    transfer = WarehouseTransfer(
        number="TR-1",
        from_warehouse_id=source.id,
        to_warehouse_id=dest.id,
        status="confirmed",
    )
    db.add(transfer)
    db.commit()
    db.add_all([
        WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=5),
        Stock(warehouse_id=source.id, product_id=product.id, quantity=5),
        Stock(warehouse_id=dest.id, product_id=product.id, quantity=2),
    ])
    db.commit()

    response = run(main.warehouse_transfer_revert(transfer.id, db, user))

    assert response.status_code == 303
    assert "error=" in response.headers["location"]
    assert stock_quantity(db, source.id, product.id) == 5
    assert stock_quantity(db, dest.id, product.id) == 2
    assert db.query(WarehouseTransfer).get(transfer.id).status == "confirmed"


def test_confirmed_purchase_cannot_be_mutated_by_add_item(db, user):
    warehouse = add_warehouse(db, "W1", "Main")
    product = add_product(db, "P1", "Halva")
    purchase = Purchase(
        number="PU-1",
        warehouse_id=warehouse.id,
        user_id=user.id,
        total=10,
        status="confirmed",
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    with pytest.raises(HTTPException) as exc:
        run(main.purchase_add_item(purchase.id, product.id, 1, 2, db, user))

    assert exc.value.status_code == 400
    assert db.query(PurchaseItem).filter_by(purchase_id=purchase.id).count() == 0
    assert db.query(Purchase).get(purchase.id).total == 10
