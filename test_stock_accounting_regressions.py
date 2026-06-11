import asyncio
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Base,
    Product,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    StockMovement,
    Warehouse,
)
from main import (
    _do_complete_production_stock,
    qoldiqlar_tovar_hujjat_revert,
    qoldiqlar_tovar_hujjat_tasdiqlash,
)
from app.models.database import Production


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return session_factory()


def test_stock_adjustment_confirm_sets_absolute_quantity_and_revert_restores_previous():
    db = make_session()
    user = SimpleNamespace(id=1)
    warehouse = Warehouse(code="WH-1", name="Main")
    product = Product(code="P-1", name="Product", type="product")
    db.add_all([warehouse, product])
    db.flush()
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    doc = StockAdjustmentDoc(number="QLD-TEST-1", status="draft", user_id=user.id)
    db.add(doc)
    db.flush()
    db.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=50,
    ))
    db.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    assert stock.quantity == 50
    movement = db.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == -50
    assert movement.quantity_after == 50

    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db, user))

    db.refresh(stock)
    db.refresh(doc)
    assert stock.quantity == 100
    assert doc.status == "draft"


def test_stock_adjustment_zero_delta_records_movement_for_safe_revert():
    db = make_session()
    user = SimpleNamespace(id=1)
    warehouse = Warehouse(code="WH-1", name="Main")
    product = Product(code="P-1", name="Product", type="product")
    db.add_all([warehouse, product])
    db.flush()
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=50))
    doc = StockAdjustmentDoc(number="QLD-TEST-2", status="draft", user_id=user.id)
    db.add(doc)
    db.flush()
    db.add(StockAdjustmentDocItem(
        doc_id=doc.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=50,
    ))
    db.commit()

    asyncio.run(qoldiqlar_tovar_hujjat_tasdiqlash(doc.id, db, user))
    asyncio.run(qoldiqlar_tovar_hujjat_revert(doc.id, db, user))

    stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=product.id).one()
    movement = db.query(StockMovement).filter_by(
        document_type="StockAdjustmentDoc",
        document_id=doc.id,
        operation_type="adjustment",
    ).one()
    assert movement.quantity_change == 0
    assert movement.quantity_after == 50
    assert stock.quantity == 50


def test_production_completion_adds_finished_goods_once():
    db = make_session()
    warehouse = Warehouse(code="WH-1", name="Main")
    raw_product = Product(code="RAW", name="Raw", type="material", purchase_price=2)
    output_product = Product(code="OUT", name="Finished", type="product", purchase_price=10)
    db.add_all([warehouse, raw_product, output_product])
    db.flush()
    db.add_all([
        Stock(warehouse_id=warehouse.id, product_id=raw_product.id, quantity=100),
        Stock(warehouse_id=warehouse.id, product_id=output_product.id, quantity=5),
    ])
    recipe = Recipe(product_id=output_product.id, name="Recipe", output_quantity=3)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=2))
    production = Production(
        number="PRD-TEST-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        quantity=2,
        status="draft",
        user_id=1,
    )
    db.add(production)
    db.commit()

    result = _do_complete_production_stock(db, production, recipe)

    assert result is None
    raw_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw_product.id).one()
    output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output_product.id).one()
    assert raw_stock.quantity == 96
    assert output_stock.quantity == 11
    output_movement = db.query(StockMovement).filter_by(
        document_type="Production",
        document_id=production.id,
        operation_type="production_output",
    ).one()
    assert output_movement.quantity_change == 6
    assert output_movement.quantity_after == 11
