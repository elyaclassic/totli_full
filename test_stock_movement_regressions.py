import asyncio
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Base,
    Product,
    Production,
    ProductionItem,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    User,
    Warehouse,
)
from main import (
    _do_complete_production_stock,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
)


def make_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def seed_user_warehouse_product(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin")
    warehouse = Warehouse(code="WH", name="Main warehouse")
    product = Product(code="P1", name="Product", type="product")
    db.add_all([user, warehouse, product])
    db.commit()
    return user, warehouse, product


def test_stock_adjustment_confirm_sets_absolute_quantity_once_and_revert_undoes_delta():
    db = make_db_session()
    try:
        user, warehouse, product = seed_user_warehouse_product(db)
        db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
        doc = StockAdjustmentDoc(number="QLD-1", date=datetime.now(), user_id=user.id, status="draft")
        db.add(doc)
        db.flush()
        db.add(
            StockAdjustmentDocItem(
                doc_id=doc.id,
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=15,
            )
        )
        db.commit()

        asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))

        stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
        assert stock.quantity == 15
        movement = db.query(StockMovement).filter_by(operation_type="adjustment").one()
        assert movement.quantity_change == 5
        assert movement.quantity_after == 15

        asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db=db, current_user=user))

        db.refresh(stock)
        assert stock.quantity == 10
        reversal = db.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
        assert reversal.quantity_change == -5
        assert reversal.quantity_after == 10
    finally:
        db.close()


def test_production_completion_adds_finished_goods_once():
    db = make_db_session()
    try:
        user = User(username="admin", password_hash="x", full_name="Admin", role="admin")
        warehouse = Warehouse(code="WH", name="Main warehouse")
        material = Product(code="M1", name="Material", type="material", purchase_price=4)
        finished = Product(code="F1", name="Finished", type="product", purchase_price=10)
        db.add_all([user, warehouse, material, finished])
        db.commit()

        recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=2)
        db.add(recipe)
        db.flush()
        db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=3))
        production = Production(
            number="PR-1",
            recipe_id=recipe.id,
            warehouse_id=warehouse.id,
            output_warehouse_id=warehouse.id,
            quantity=4,
            status="draft",
            user_id=user.id,
        )
        db.add(production)
        db.flush()
        db.add(ProductionItem(production_id=production.id, product_id=material.id, quantity=12))
        db.add_all(
            [
                Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=20),
                Stock(warehouse_id=warehouse.id, product_id=finished.id, quantity=10),
            ]
        )
        db.commit()

        result = _do_complete_production_stock(db, production, recipe)

        assert result is None
        material_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=material.id).one()
        finished_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=finished.id).one()
        assert material_stock.quantity == 8
        assert finished_stock.quantity == 18

        output_movement = db.query(StockMovement).filter_by(operation_type="production_output").one()
        assert output_movement.quantity_change == 8
        assert output_movement.quantity_after == 18
    finally:
        db.close()
