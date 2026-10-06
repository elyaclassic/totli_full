"""Re-importing the product catalog must not resurrect deleted products or wipe category."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, Category, Product, Unit
from app.utils.product_import import upsert_product_from_import


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_reimport_keeps_inactive_and_category():
    db = _session()
    category = Category(code="HALVA", name="Halva", type="tayyor")
    unit = Unit(code="kg", name="kg")
    db.add_all([category, unit])
    db.flush()
    existing = Product(
        code="P00001",
        name="Eski holva",
        type="tayyor",
        category_id=category.id,
        unit_id=unit.id,
        sale_price=15000,
        purchase_price=10000,
        is_active=False,
        barcode="123",
    )
    db.add(existing)
    db.commit()

    created = upsert_product_from_import(
        db,
        code="P00001",
        name="Holva yangi nom",
        type_="tayyor",
        unit=unit,
        sale_price=16000,
        purchase_price=11000,
    )
    db.commit()
    db.refresh(existing)

    assert created is False
    assert existing.is_active is False
    assert existing.category_id == category.id
    assert existing.name == "Holva yangi nom"
    assert existing.sale_price == 16000
    assert existing.purchase_price == 11000
    assert existing.barcode == "123"
    assert existing.unit_id == unit.id


def test_reimport_without_unit_does_not_clear_category_or_reactivate():
    db = _session()
    category = Category(code="XOM", name="Xom ashyo", type="hom_ashyo")
    unit = Unit(code="kg", name="kg")
    db.add_all([category, unit])
    db.flush()
    existing = Product(
        code="P00002",
        name="Yong'oq",
        type="hom_ashyo",
        category_id=category.id,
        unit_id=unit.id,
        is_active=False,
    )
    db.add(existing)
    db.commit()

    upsert_product_from_import(
        db,
        code="P00002",
        name="Yong'oq",
        type_="hom_ashyo",
        unit=None,
        sale_price=2000,
        purchase_price=1500,
    )
    db.commit()
    db.refresh(existing)

    assert existing.is_active is False
    assert existing.category_id == category.id


def test_new_import_row_is_active_without_category():
    db = _session()
    unit = Unit(code="dona", name="dona")
    db.add(unit)
    db.commit()

    created = upsert_product_from_import(
        db,
        code="P00009",
        name="Yangi tovar",
        type_="tayyor",
        unit=unit,
        sale_price=5000,
        purchase_price=3000,
    )
    db.commit()
    product = db.query(Product).filter(Product.code == "P00009").one()

    assert created is True
    assert product.is_active is True
    assert product.category_id is None
    assert product.unit_id == unit.id
    assert product.sale_price == 5000
