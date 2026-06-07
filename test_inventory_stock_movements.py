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
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def create_user_product_and_warehouse(db):
    user = User(username="admin", password_hash="x", full_name="Admin", role="admin")
    product = Product(code="P1", name="Test product", type="product")
    warehouse = Warehouse(code="WH1", name="Main warehouse")
    db.add_all([user, product, warehouse])
    db.commit()
    return user, product, warehouse


def test_stock_adjustment_sets_absolute_quantity_and_reverts_delta():
    db = make_session()
    user, product, warehouse = create_user_product_and_warehouse(db)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    doc = StockAdjustmentDoc(number="ADJ-1", user_id=user.id, status="draft")
    db.add(doc)
    db.flush()
    db.add(
        StockAdjustmentDocItem(
            doc_id=doc.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=15,
        )
    )
    db.commit()

    asyncio.run(main.qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 15
    movement = db.query(StockMovement).filter_by(operation_type="adjustment").one()
    assert movement.quantity_change == 5
    assert movement.quantity_after == 15

    asyncio.run(main.qoldiqlar_tovar_hujjat_revert(doc.id, db, user))

    db.refresh(stock)
    assert stock.quantity == 10
    reverse = db.query(StockMovement).filter_by(operation_type="adjustment_revert").one()
    assert reverse.quantity_change == -5
    assert reverse.quantity_after == 10


def test_production_completion_adds_finished_goods_once_to_existing_stock():
    db = make_session()
    user, material, source_warehouse = create_user_product_and_warehouse(db)
    finished = Product(code="FG1", name="Finished good", type="product", purchase_price=4)
    output_warehouse = Warehouse(code="WH2", name="Output warehouse")
    db.add_all([finished, output_warehouse])
    db.flush()
    recipe = Recipe(product_id=finished.id, name="Recipe", output_quantity=1)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=1))
    db.add(Stock(warehouse_id=source_warehouse.id, product_id=material.id, quantity=10))
    db.add(Stock(warehouse_id=output_warehouse.id, product_id=finished.id, quantity=7))
    production = Production(
        number="PROD-1",
        recipe_id=recipe.id,
        warehouse_id=source_warehouse.id,
        output_warehouse_id=output_warehouse.id,
        quantity=5,
        user_id=user.id,
    )
    db.add(production)
    db.commit()

    result = main._do_complete_production_stock(db, production, recipe)
    db.flush()

    assert result is None
    material_stock = db.query(Stock).filter_by(warehouse_id=source_warehouse.id, product_id=material.id).one()
    output_stock = db.query(Stock).filter_by(warehouse_id=output_warehouse.id, product_id=finished.id).one()
    assert material_stock.quantity == 5
    assert output_stock.quantity == 12
    output_movement = db.query(StockMovement).filter_by(operation_type="production_output").one()
    assert output_movement.quantity_change == 5
    assert output_movement.quantity_after == 12


def test_production_completion_creates_one_finished_good_stock_row():
    db = make_session()
    user, material, warehouse = create_user_product_and_warehouse(db)
    finished = Product(code="FG2", name="New finished good", type="product")
    db.add(finished)
    db.flush()
    recipe = Recipe(product_id=finished.id, name="New stock recipe", output_quantity=1)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=1))
    db.add(Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=10))
    production = Production(
        number="PROD-2",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=5,
        user_id=user.id,
    )
    db.add(production)
    db.commit()

    result = main._do_complete_production_stock(db, production, recipe)
    db.flush()

    assert result is None
    output_rows = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=finished.id).all()
    assert len(output_rows) == 1
    assert output_rows[0].quantity == 5
