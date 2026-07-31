"""Regression: product Excel import must not wipe prices when cells are blank."""
import asyncio
import io

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

import main
from app.models.database import Base, Product, User


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _Upload:
    def __init__(self, data: bytes, filename: str = "products.xlsx"):
        self.filename = filename
        self._data = data

    async def read(self):
        return self._data


class _Form(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


class _Request:
    def __init__(self, form):
        self._form = form

    async def form(self):
        return self._form


def _xlsx_bytes(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Kod", "Nomi", "Turi", "O'lchov", "Sotish narxi", "Olish narxi"])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_import_blank_prices_preserve_existing(db):
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    db.add(user)
    product = Product(
        code="P001",
        name="Old name",
        type="tayyor",
        is_active=True,
        sale_price=15000,
        purchase_price=10000,
    )
    db.add(product)
    db.commit()

    content = _xlsx_bytes([["", "P001", "New name", "tayyor", "dona", "", ""]])
    request = _Request(_Form(file=_Upload(content)))
    resp = run(main.import_products(request, db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    assert "import_ok=1" in (resp.headers.get("location") or "")

    db.refresh(product)
    assert product.name == "New name"
    assert product.sale_price == 15000
    assert product.purchase_price == 10000


def test_import_explicit_prices_update_existing(db):
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    db.add(user)
    product = Product(
        code="P002",
        name="Widget",
        type="tayyor",
        is_active=True,
        sale_price=15000,
        purchase_price=10000,
    )
    db.add(product)
    db.commit()

    content = _xlsx_bytes([["", "P002", "Widget", "tayyor", "dona", 18000, 0]])
    request = _Request(_Form(file=_Upload(content)))
    resp = run(main.import_products(request, db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    assert "import_ok=1" in (resp.headers.get("location") or "")

    db.refresh(product)
    assert product.sale_price == 18000
    assert product.purchase_price == 0


def test_import_new_product_blank_prices_default_zero(db):
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    db.add(user)
    db.commit()

    content = _xlsx_bytes([["", "P003", "Brand new", "tayyor", "dona", None, None]])
    request = _Request(_Form(file=_Upload(content)))
    resp = run(main.import_products(request, db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    assert "import_ok=1" in (resp.headers.get("location") or "")

    product = db.query(Product).filter(Product.code == "P003").first()
    assert product is not None
    assert product.sale_price == 0
    assert product.purchase_price == 0
