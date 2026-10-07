"""Edited raw-material quantities on /production/new must be stored on the order."""
import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.models.database import (
    Base,
    Product,
    Recipe,
    RecipeItem,
    Warehouse,
    ProductionItem,
)
from main import _material_qty_overrides, create_production


def test_overrides_keep_zero_and_skip_invalid():
    overrides = _material_qty_overrides(
        ["3", "4", "x", "5"],
        ["0", "-2", "1", "1,5"],
    )
    assert overrides[3] == 0
    assert 4 not in overrides
    assert overrides[5] == 1.5


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _request(body: str) -> Request:
    raw = body.encode()

    async def receive():
        return {"type": "http.request", "body": raw, "more_body": False}

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/production/create",
        "raw_path": b"/production/create",
        "query_string": b"",
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    return Request(scope, receive)


def _seed(db):
    wh = Warehouse(name="Xom", code="XOM", is_active=True)
    sugar = Product(name="Shakar", code="SHAKAR", type="hom_ashyo", is_active=True)
    flour = Product(name="Un", code="UN", type="hom_ashyo", is_active=True)
    finished = Product(name="Halva", code="HALVA", type="tayyor", is_active=True)
    db.add_all([wh, sugar, flour, finished])
    db.commit()
    recipe = Recipe(name="Halva", product_id=finished.id, output_quantity=1, is_active=True)
    db.add(recipe)
    db.commit()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=sugar.id, quantity=2))
    db.add(RecipeItem(recipe_id=recipe.id, product_id=flour.id, quantity=1))
    db.commit()
    return wh, sugar, flour, recipe


def _items(db, production_id):
    rows = (
        db.query(ProductionItem)
        .filter(ProductionItem.production_id == production_id)
        .all()
    )
    return {row.product_id: row.quantity for row in rows}


def test_create_stores_edited_material_quantities():
    db = _session()
    wh, sugar, flour, recipe = _seed(db)
    body = (
        f"recipe_id={recipe.id}&warehouse_id={wh.id}&quantity=10"
        f"&material_product_id={sugar.id}&material_quantity=5"
        f"&material_product_id={flour.id}&material_quantity=0"
    )
    response = asyncio.run(
        create_production(
            request=_request(body),
            recipe_id=recipe.id,
            warehouse_id=wh.id,
            output_warehouse_id=None,
            quantity=10,
            note="",
            machine_id=None,
            operator_id=None,
            db=db,
            current_user=None,
        )
    )
    assert response.status_code == 303
    stored = _items(db, 1)
    # Recipe would have used 2*10=20 and 1*10=10. The form edits must win.
    assert stored[sugar.id] == 5
    assert stored[flour.id] == 0


def test_create_without_material_fields_uses_recipe():
    db = _session()
    wh, sugar, flour, recipe = _seed(db)
    body = f"recipe_id={recipe.id}&warehouse_id={wh.id}&quantity=10"
    asyncio.run(
        create_production(
            request=_request(body),
            recipe_id=recipe.id,
            warehouse_id=wh.id,
            output_warehouse_id=None,
            quantity=10,
            note="",
            machine_id=None,
            operator_id=None,
            db=db,
            current_user=None,
        )
    )
    stored = _items(db, 1)
    assert stored[sugar.id] == 20
    assert stored[flour.id] == 10


def test_new_order_template_submits_material_fields():
    text = open("app/templates/production/new_order.html", encoding="utf-8").read()
    assert 'form="productionForm"' in text
    assert 'name="material_product_id"' in text
    assert 'name="material_quantity"' in text
    assert "material_product_id[]" not in text
