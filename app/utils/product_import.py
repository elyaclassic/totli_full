"""Apply one product row from the catalog Excel sheet.

The sheet columns are ID, code, name, type, unit, sale price, purchase price.
There is no active flag and no category column, so a re-import of the export
file must not turn a soft-deleted product back on or clear its category.
"""
from app.models.database import Product


def upsert_product_from_import(db, *, code, name, type_, unit, sale_price, purchase_price) -> bool:
    """Insert or update a product matched by code. Returns True when created."""
    product = db.query(Product).filter(Product.code == code).first()
    is_new = product is None
    if is_new:
        product = Product(code=code, is_active=True)
        db.add(product)
    product.name = name
    product.type = type_
    product.unit_id = unit.id if unit else None
    product.sale_price = sale_price
    product.purchase_price = purchase_price
    return is_new
