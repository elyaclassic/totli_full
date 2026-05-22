import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
from main import _do_complete_production_stock, qoldiqlar_tovar_hujjat_tasdiqlash


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def test_stock_adjustment_confirmation_sets_absolute_quantity_once():
    db = make_session()
    try:
        user = User(username="admin", password_hash="x", full_name="Admin", role="admin")
        warehouse = Warehouse(code="WH", name="Warehouse")
        product = Product(code="P1", name="Product", type="product")
        db.add_all([user, warehouse, product])
        db.flush()
        db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
        doc = StockAdjustmentDoc(number="QLD-1", user_id=user.id, status="draft")
        db.add(doc)
        db.flush()
        db.add(
            StockAdjustmentDocItem(
                doc_id=doc.id,
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=80,
            )
        )
        db.commit()

        asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db=db, current_user=user))

        stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
        movement = db.query(StockMovement).filter_by(document_type="StockAdjustmentDoc", document_id=doc.id).one()
        assert stock.quantity == 80
        assert movement.quantity_change == -20
        assert movement.quantity_after == 80
    finally:
        db.close()


def test_production_completion_adds_output_stock_once():
    db = make_session()
    try:
        raw_warehouse = Warehouse(code="RAW", name="Raw")
        output_warehouse = Warehouse(code="OUT", name="Output")
        raw_product = Product(code="RAW-P", name="Raw product", type="material", purchase_price=2)
        finished_product = Product(code="FIN-P", name="Finished product", type="product", purchase_price=5)
        db.add_all([raw_warehouse, output_warehouse, raw_product, finished_product])
        db.flush()

        recipe = Recipe(product_id=finished_product.id, name="Recipe", output_quantity=1)
        db.add(recipe)
        db.flush()
        db.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=2))
        production = Production(
            number="PR-1",
            recipe_id=recipe.id,
            warehouse_id=raw_warehouse.id,
            output_warehouse_id=output_warehouse.id,
            quantity=3,
            user_id=None,
        )
        db.add(production)
        db.add_all(
            [
                Stock(warehouse_id=raw_warehouse.id, product_id=raw_product.id, quantity=10),
                Stock(warehouse_id=output_warehouse.id, product_id=finished_product.id, quantity=4),
            ]
        )
        db.commit()

        err = _do_complete_production_stock(db, production, recipe)
        db.flush()

        assert err is None
        raw_stock = db.query(Stock).filter_by(warehouse_id=raw_warehouse.id, product_id=raw_product.id).one()
        output_stock = db.query(Stock).filter_by(warehouse_id=output_warehouse.id, product_id=finished_product.id).one()
        output_movement = db.query(StockMovement).filter_by(
            document_type="Production",
            document_id=production.id,
            operation_type="production_output",
        ).one()
        assert raw_stock.quantity == 4
        assert output_stock.quantity == 7
        assert output_movement.quantity_change == 3
        assert output_movement.quantity_after == 7
    finally:
        db.close()
