import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main as app_module
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
)


def make_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'inventory.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_stock_adjustment_sets_absolute_quantity_once_and_reverts_delta(tmp_path):
    db = make_session(tmp_path)
    try:
        user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
        warehouse = Warehouse(code="WH1", name="Main", is_active=True)
        product = Product(code="P1", name="Halva", type="product", is_active=True)
        db.add_all([user, warehouse, product])
        db.commit()
        db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
        doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
        db.add(doc)
        db.commit()
        db.add(
            StockAdjustmentDocItem(
                doc_id=doc.id,
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=50,
            )
        )
        db.commit()

        asyncio.run(
            app_module.qoldiqlar_tovar_hujjat_tasdiqlash(
                doc_id=doc.id,
                db=db,
                current_user=user,
            )
        )

        stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
        movement = db.query(StockMovement).filter_by(document_type="StockAdjustmentDoc", document_id=doc.id).one()
        assert stock.quantity == 50
        assert movement.quantity_change == 40
        assert movement.quantity_after == 50

        asyncio.run(
            app_module.qoldiqlar_tovar_hujjat_revert(
                doc_id=doc.id,
                db=db,
                current_user=user,
            )
        )

        assert stock.quantity == 10
        assert doc.status == "draft"
    finally:
        db.close()


def test_production_completion_credits_output_stock_once(tmp_path):
    db = make_session(tmp_path)
    try:
        raw_warehouse = Warehouse(code="RAW", name="Raw", is_active=True)
        output_warehouse = Warehouse(code="OUT", name="Output", is_active=True)
        material = Product(code="M1", name="Sugar", type="material", purchase_price=2, is_active=True)
        finished = Product(code="F1", name="Finished Halva", type="product", purchase_price=0, is_active=True)
        db.add_all([raw_warehouse, output_warehouse, material, finished])
        db.commit()
        recipe = Recipe(product_id=finished.id, name="Halva recipe", output_quantity=1, is_active=True)
        db.add(recipe)
        db.commit()
        db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=3))
        production = Production(
            number="PR-1",
            recipe_id=recipe.id,
            warehouse_id=raw_warehouse.id,
            output_warehouse_id=output_warehouse.id,
            quantity=2,
            status="draft",
        )
        db.add_all([
            Stock(warehouse_id=raw_warehouse.id, product_id=material.id, quantity=100),
            production,
        ])
        db.commit()

        error_response = app_module._do_complete_production_stock(db, production, recipe)
        db.commit()

        assert error_response is None
        raw_stock = db.query(Stock).filter_by(warehouse_id=raw_warehouse.id, product_id=material.id).one()
        output_stock = db.query(Stock).filter_by(warehouse_id=output_warehouse.id, product_id=finished.id).one()
        output_movement = db.query(StockMovement).filter_by(
            document_type="Production",
            document_id=production.id,
            operation_type="production_output",
        ).one()
        assert raw_stock.quantity == 94
        assert output_stock.quantity == 2
        assert output_movement.quantity_change == 2
        assert output_movement.quantity_after == 2
        assert finished.purchase_price == 6
    finally:
        db.close()


def test_completed_production_delete_is_blocked(tmp_path):
    db = make_session(tmp_path)
    try:
        user = User(username="admin", password_hash="x", full_name="Admin", role="admin", is_active=True)
        warehouse = Warehouse(code="WH1", name="Main", is_active=True)
        finished = Product(code="F2", name="Finished Product", type="product", is_active=True)
        db.add_all([user, warehouse, finished])
        db.commit()
        recipe = Recipe(product_id=finished.id, name="Finished recipe", output_quantity=1, is_active=True)
        db.add(recipe)
        db.commit()
        production = Production(
            number="PR-DONE",
            recipe_id=recipe.id,
            warehouse_id=warehouse.id,
            quantity=1,
            status="completed",
            user_id=user.id,
        )
        db.add(production)
        db.commit()

        response = asyncio.run(
            app_module.delete_production(
                prod_id=production.id,
                db=db,
                current_user=user,
            )
        )

        assert response.status_code == 303
        assert db.query(Production).filter_by(id=production.id).one().status == "completed"
    finally:
        db.close()
