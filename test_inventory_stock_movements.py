import asyncio
from types import SimpleNamespace

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
    Warehouse,
)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSession()


def test_stock_adjustment_confirmation_sets_exact_quantity_once():
    db = make_session()
    try:
        product = Product(name="Material", type="material")
        warehouse = Warehouse(code="W1", name="Warehouse 1")
        db.add_all([product, warehouse])
        db.flush()
        db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=5))
        doc = StockAdjustmentDoc(number="ADJ-1", status="draft")
        db.add(doc)
        db.flush()
        db.add(
            StockAdjustmentDocItem(
                doc_id=doc.id,
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=8,
            )
        )
        db.commit()

        asyncio.run(
            main.qoldiqlar_tovar_hujjat_tasdiqlash(
                doc_id=doc.id,
                db=db,
                current_user=SimpleNamespace(id=1),
            )
        )

        stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
        movement = db.query(StockMovement).filter_by(document_type="StockAdjustmentDoc").one()
        assert stock.quantity == 8
        assert movement.quantity_change == 3
        assert movement.quantity_after == 8
    finally:
        db.close()


def test_complete_production_adds_output_stock_once():
    db = make_session()
    try:
        material = Product(name="Sugar", type="material", purchase_price=4)
        output = Product(name="Halva", type="product", purchase_price=10)
        warehouse = Warehouse(code="W1", name="Warehouse 1")
        db.add_all([material, output, warehouse])
        db.flush()
        db.add_all(
            [
                Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=10),
                Stock(warehouse_id=warehouse.id, product_id=output.id, quantity=10),
            ]
        )
        recipe = Recipe(product_id=output.id, name="Halva recipe", output_quantity=3)
        db.add(recipe)
        db.flush()
        db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=1))
        production = Production(
            number="PROD-1",
            recipe_id=recipe.id,
            warehouse_id=warehouse.id,
            quantity=2,
            status="draft",
            user_id=1,
        )
        db.add(production)
        db.commit()
        db.refresh(recipe)
        db.refresh(production)

        err = main._do_complete_production_stock(db, production, recipe)
        assert err is None
        db.commit()

        material_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
        output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output.id).one()
        output_movement = db.query(StockMovement).filter_by(operation_type="production_output").one()
        assert material_stock.quantity == 8
        assert output_stock.quantity == 16
        assert output_movement.quantity_change == 6
        assert output_movement.quantity_after == 16
    finally:
        db.close()
