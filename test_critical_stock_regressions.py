import asyncio
import inspect

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.routes import info as info_routes
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
    Production,
)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _admin(db):
    user = User(username="admin", password_hash="x", role="admin", is_active=True)
    db.add(user)
    db.flush()
    return user


def _warehouse(db):
    warehouse = Warehouse(code="WH", name="Warehouse")
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


def test_stock_adjustment_confirm_and_revert_use_delta_movements(db_session):
    user = _admin(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session, "P1", "Product")
    db_session.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=5,
        )
    )
    db_session.commit()

    asyncio.run(
        main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user)
    )

    stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=product.id,
    ).one()
    assert stock.quantity == 5
    adjustment = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert adjustment.quantity_change == -5
    assert adjustment.quantity_after == 5

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))

    db_session.refresh(stock)
    assert stock.quantity == 10
    revert = db_session.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment_revert",
    ).one()
    assert revert.quantity_change == 5
    assert revert.quantity_after == 10

    # A later confirm/revert cycle must only reverse the newest adjustment movement.
    asyncio.run(
        main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db_session, current_user=user)
    )
    db_session.refresh(stock)
    assert stock.quantity == 5
    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db=db_session, current_user=user))
    db_session.refresh(stock)
    assert stock.quantity == 10


def test_production_completion_adds_output_once_and_is_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda db: 0)
    user = _admin(db_session)
    warehouse = _warehouse(db_session)
    material = _product(db_session, "M1", "Material", product_type="material", purchase_price=2)
    output = _product(db_session, "P2", "Finished", purchase_price=10)
    db_session.add_all(
        [
            Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=10),
            Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=1),
        ]
    )
    recipe = Recipe(product_id=output.id, name="Recipe", output_quantity=2, is_active=True)
    db_session.add(recipe)
    db_session.flush()
    db_session.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=3))
    production = Production(
        number="PR-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=1,
        status="draft",
        user_id=user.id,
    )
    db_session.add(production)
    db_session.commit()

    asyncio.run(main.complete_production(production.id, db=db_session, current_user=user))

    material_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=material.id,
    ).one()
    output_stock = db_session.query(Stock).filter_by(
        warehouse_id=warehouse.id,
        product_id=output.id,
    ).one()
    assert material_stock.quantity == 7
    assert output_stock.quantity == 3
    assert (
        db_session.query(StockMovement)
        .filter_by(document_type="Production", document_id=production.id)
        .count()
        == 2
    )

    asyncio.run(main.complete_production(production.id, db=db_session, current_user=user))

    db_session.refresh(material_stock)
    db_session.refresh(output_stock)
    assert material_stock.quantity == 7
    assert output_stock.quantity == 3
    assert (
        db_session.query(StockMovement)
        .filter_by(document_type="Production", document_id=production.id)
        .count()
        == 2
    )


def test_confirmed_purchase_rejects_late_item_mutation(db_session):
    user = _admin(db_session)
    warehouse = _warehouse(db_session)
    product = _product(db_session, "P3", "Purchase Product")
    purchase = Purchase(
        number="PUR-1",
        warehouse_id=warehouse.id,
        user_id=user.id,
        total=100,
        status="confirmed",
    )
    db_session.add(purchase)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            main.purchase_add_item(
                purchase.id,
                product_id=product.id,
                quantity=2,
                price=3,
                db=db_session,
                current_user=user,
            )
        )

    assert exc.value.status_code == 400
    assert db_session.query(PurchaseItem).filter_by(purchase_id=purchase.id).count() == 0
    db_session.refresh(purchase)
    assert purchase.total == 100


def test_destructive_routes_require_admin_dependency():
    endpoints = [
        main.product_delete,
        main.partner_delete,
        main.cancel_production,
        info_routes.info_warehouses_delete,
        info_routes.info_cash_delete,
        info_routes.region_delete,
    ]

    for endpoint in endpoints:
        current_user = inspect.signature(endpoint).parameters["current_user"]
        assert current_user.default.dependency is main.require_admin
