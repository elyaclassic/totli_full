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
from main import (
    _do_complete_production_stock,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_stock_adjustment_confirm_and_revert_apply_only_delta():
    db = _session()
    admin = User(username="admin", password_hash="x", role="admin", is_active=True)
    warehouse = Warehouse(name="Main", is_active=True)
    product = Product(name="Holva", type="product", is_active=True)
    db.add_all([admin, warehouse, product])
    db.flush()
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    doc = StockAdjustmentDoc(number="QLD-TEST", user_id=admin.id, status="draft")
    db.add(doc)
    db.flush()
    db.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        quantity=150,
    ))
    db.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, admin))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 150
    movement = db.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 50
    assert movement.quantity_after == 150

    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db, admin))

    db.refresh(stock)
    assert stock.quantity == 100
    net_change = sum(
        m.quantity_change
        for m in db.query(StockMovement).filter_by(
            document_type="StockAdjustmentDoc",
            document_id=doc.id,
        )
    )
    assert net_change == 0


def test_production_completion_adds_finished_goods_once():
    db = _session()
    input_wh = Warehouse(name="Input", is_active=True)
    output_wh = Warehouse(name="Output", is_active=True)
    material = Product(name="Sugar", type="material", purchase_price=2, is_active=True)
    finished = Product(name="Finished", type="product", purchase_price=4, is_active=True)
    db.add_all([input_wh, output_wh, material, finished])
    db.flush()
    db.add_all([
        Stock(warehouse_id=input_wh.id, product_id=material.id, quantity=100),
        Stock(warehouse_id=output_wh.id, product_id=finished.id, quantity=10),
    ])
    recipe = Recipe(product_id=finished.id, name="Finished recipe", output_quantity=1)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    production = Production(
        number="PR-TEST",
        recipe_id=recipe.id,
        warehouse_id=input_wh.id,
        output_warehouse_id=output_wh.id,
        quantity=5,
        status="draft",
    )
    db.add(production)
    db.commit()

    err = _do_complete_production_stock(db, production, recipe)
    db.commit()

    assert err is None
    material_stock = db.query(Stock).filter_by(warehouse_id=input_wh.id, product_id=material.id).one()
    finished_stock = db.query(Stock).filter_by(warehouse_id=output_wh.id, product_id=finished.id).one()
    assert material_stock.quantity == 90
    assert finished_stock.quantity == 15
    output_movement = db.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert output_movement.quantity_change == 5
    assert output_movement.quantity_after == 15
