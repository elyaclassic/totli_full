import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from app.models.database import (
    Base,
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


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    return db, engine


def _user(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
    db.add(user)
    db.commit()
    return user


def _warehouse(db, code="WH"):
    warehouse = Warehouse(code=code, name=code)
    db.add(warehouse)
    db.commit()
    return warehouse


def _product(db, name="Product", product_type="product", purchase_price=0):
    product = Product(name=name, type=product_type, purchase_price=purchase_price, sale_price=0, is_active=True)
    db.add(product)
    db.commit()
    return product


def test_stock_adjustment_confirm_and_revert_apply_recorded_delta_once(tmp_path):
    db, engine = _session(tmp_path)
    try:
        user = _user(db)
        warehouse = _warehouse(db)
        product = _product(db)
        stock = Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10)
        doc = StockAdjustmentDoc(number="SA-1", user_id=user.id, status="draft")
        db.add_all([stock, doc])
        db.commit()
        item = StockAdjustmentDocItem(
            doc_id=doc.id,
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=15,
            cost_price=0,
            sale_price=0,
        )
        db.add(item)
        db.commit()

        asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))

        db.refresh(stock)
        db.refresh(doc)
        assert doc.status == "confirmed"
        assert stock.quantity == 15
        movement = db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment",
        ).one()
        assert movement.quantity_change == 5
        assert movement.quantity_after == 15

        asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db, user))

        db.refresh(stock)
        db.refresh(doc)
        assert doc.status == "draft"
        assert stock.quantity == 10
        revert = db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
            operation_type="adjustment_revert",
        ).one()
        assert revert.quantity_change == -5
        assert revert.quantity_after == 10
    finally:
        db.close()
        engine.dispose()


def test_production_completion_adds_finished_stock_once(tmp_path):
    db, engine = _session(tmp_path)
    try:
        user = _user(db)
        warehouse = _warehouse(db)
        material = _product(db, name="Material", product_type="material", purchase_price=4)
        finished = _product(db, name="Finished", product_type="product", purchase_price=2)
        db.add_all([
            Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=100),
            Stock(warehouse_id=warehouse.id, product_id=finished.id, quantity=4),
        ])
        db.commit()
        recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=2, is_active=True)
        db.add(recipe)
        db.commit()
        db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=1))
        production = Production(
            number="PR-1",
            recipe_id=recipe.id,
            warehouse_id=warehouse.id,
            output_warehouse_id=warehouse.id,
            quantity=3,
            status="in_progress",
            user_id=user.id,
        )
        db.add(production)
        db.commit()

        result = main._do_complete_production_stock(db, production, recipe)

        assert result is None
        material_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
        finished_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=finished.id).one()
        assert material_stock.quantity == 97
        assert finished_stock.quantity == 10
        output_movement = db.query(StockMovement).filter_by(
            document_type="Production",
            document_id=production.id,
            operation_type="production_output",
        ).one()
        assert output_movement.quantity_change == 6
        assert output_movement.quantity_after == 10
    finally:
        db.close()
        engine.dispose()


def test_transfer_revert_refuses_when_destination_stock_was_consumed(tmp_path):
    db, engine = _session(tmp_path)
    try:
        user = _user(db)
        source = _warehouse(db, code="SRC")
        destination = _warehouse(db, code="DST")
        product = _product(db)
        transfer = WarehouseTransfer(
            number="TR-1",
            from_warehouse_id=source.id,
            to_warehouse_id=destination.id,
            status="confirmed",
            user_id=user.id,
            approved_by_user_id=user.id,
        )
        db.add(transfer)
        db.commit()
        db.add_all([
            WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=5),
            Stock(warehouse_id=source.id, product_id=product.id, quantity=0),
            Stock(warehouse_id=destination.id, product_id=product.id, quantity=2),
        ])
        db.commit()

        response = asyncio.run(main.warehouse_transfer_revert(transfer.id, db, user))

        db.refresh(transfer)
        source_stock = db.query(Stock).filter_by(warehouse_id=source.id, product_id=product.id).one()
        destination_stock = db.query(Stock).filter_by(warehouse_id=destination.id, product_id=product.id).one()
        assert response.status_code == 303
        assert "error=" in response.headers["location"]
        assert transfer.status == "confirmed"
        assert source_stock.quantity == 0
        assert destination_stock.quantity == 2
    finally:
        db.close()
        engine.dispose()
