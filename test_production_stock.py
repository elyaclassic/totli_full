from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Base,
    Category,
    Product,
    Production,
    ProductionItem,
    Recipe,
    RecipeItem,
    Stock,
    StockMovement,
    Unit,
    Warehouse,
)
from main import _do_complete_production_stock


def test_complete_production_adds_finished_goods_once():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    db = session()

    unit = Unit(code="kg", name="Kilogram")
    category = Category(code="test", name="Test", type="product")
    raw_product = Product(
        code="RAW",
        name="Raw material",
        type="material",
        unit=unit,
        category=category,
        purchase_price=2,
        is_active=True,
    )
    output_product = Product(
        code="OUT",
        name="Finished good",
        type="product",
        unit=unit,
        category=category,
        purchase_price=10,
        is_active=True,
    )
    warehouse = Warehouse(code="WH", name="Warehouse", is_active=True)
    db.add_all([unit, category, raw_product, output_product, warehouse])
    db.flush()

    recipe = Recipe(
        name="Finished good recipe",
        product_id=output_product.id,
        output_quantity=1,
        is_active=True,
    )
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=raw_product.id, quantity=2))

    production = Production(
        number="PR-TEST",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        output_warehouse_id=warehouse.id,
        quantity=5,
        status="draft",
    )
    db.add(production)
    db.flush()
    db.add(ProductionItem(production_id=production.id, product_id=raw_product.id, quantity=10))
    db.add(Stock(warehouse_id=warehouse.id, product_id=raw_product.id, quantity=100))
    db.add(Stock(warehouse_id=warehouse.id, product_id=output_product.id, quantity=10))
    db.commit()

    recipe = db.query(Recipe).filter_by(id=recipe.id).one()
    production = db.query(Production).filter_by(id=production.id).one()

    err = _do_complete_production_stock(db, production, recipe)

    assert err is None
    raw_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=raw_product.id).one()
    output_stock = db.query(Stock).filter_by(warehouse_id=warehouse.id, product_id=output_product.id).one()
    output_movement = (
        db.query(StockMovement)
        .filter_by(product_id=output_product.id, operation_type="production_output")
        .one()
    )

    assert raw_stock.quantity == 90
    assert output_stock.quantity == 15
    assert output_movement.quantity_change == 5
    assert output_movement.quantity_after == 15
