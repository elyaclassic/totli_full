"""Regression: blank Excel qty wipe, legacy qoldiqlar mutators, zero-material production."""
import asyncio
import io
from datetime import datetime
from urllib.parse import unquote

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

import main
from app.models.database import (
    Base,
    CashRegister,
    Partner,
    Product,
    Production,
    ProductionItem,
    Recipe,
    RecipeItem,
    Stock,
    StockMovement,
    User,
    Warehouse,
)
from app.routes import reports as reports_routes


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
    def __init__(self, data: bytes, filename: str = "stock.xlsx"):
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


def _stock_xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Ombor", "Mahsulot", "Qoldiq", "Tannarx", "Sotuv"])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_warehouse_import_blank_qty_preserves_stock(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    product = Product(code="P100", name="Yong'oq", type="xom", is_active=True, sale_price=1, purchase_price=1)
    db.add_all([user, wh, product])
    db.flush()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=80)
    db.add(stock)
    db.commit()

    content = _stock_xlsx([["Asosiy", "P100", "", "", ""]])
    resp = run(main.warehouse_import(_Request(_Form(file=_Upload(content))), db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)

    db.refresh(stock)
    assert stock.quantity == 80


def test_warehouse_import_explicit_zero_sets_stock(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    product = Product(code="P101", name="Bodom", type="xom", is_active=True, sale_price=1, purchase_price=1)
    db.add_all([user, wh, product])
    db.flush()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=80)
    db.add(stock)
    db.commit()

    content = _stock_xlsx([["Asosiy", "P101", 0, "", ""]])
    resp = run(main.warehouse_import(_Request(_Form(file=_Upload(content))), db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    assert "success=import" in (resp.headers.get("location") or "")

    db.refresh(stock)
    assert stock.quantity == 0


def test_reports_stock_import_blank_qty_preserves_stock(db):
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    product = Product(code="P102", name="Un", type="xom", is_active=True, sale_price=1, purchase_price=1)
    db.add_all([user, wh, product])
    db.flush()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=55)
    db.add(stock)
    db.commit()

    content = _stock_xlsx([["Asosiy", "P102", None, "", ""]])
    resp = run(reports_routes.report_stock_import(_Upload(content), db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)

    db.refresh(stock)
    assert stock.quantity == 55


def test_legacy_qoldiqlar_tovar_does_not_mutate_stock(db):
    user = User(username="u1", full_name="User", password_hash="x", role="user", is_active=True)
    wh = Warehouse(name="Asosiy", code="WH1", is_active=True)
    product = Product(code="P200", name="Halva", type="tayyor", is_active=True, sale_price=1, purchase_price=1)
    db.add_all([user, wh, product])
    db.flush()
    stock = Stock(warehouse_id=wh.id, product_id=product.id, quantity=10)
    db.add(stock)
    db.commit()

    resp = run(main.qoldiqlar_tovar_save(warehouse_id=wh.id, product_id=product.id, quantity=500, db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    assert "legacy" in (resp.headers.get("location") or "")

    db.refresh(stock)
    assert stock.quantity == 10
    assert db.query(StockMovement).count() == 0


def test_legacy_qoldiqlar_kassa_and_partner_do_not_wipe_balances(db):
    user = User(username="u1", full_name="User", password_hash="x", role="user", is_active=True)
    cash = CashRegister(name="Kassa 1", code="C1", balance=1000, is_active=True)
    partner = Partner(name="Klient", code="K1", balance=8000, is_active=True)
    db.add_all([user, cash, partner])
    db.commit()

    cash_resp = run(main.qoldiqlar_kassa_save(cash_id=cash.id, balance=0, db=db, current_user=user))
    partner_resp = run(main.qoldiqlar_kontragent_save(partner_id=partner.id, balance="0", db=db, current_user=user))
    assert isinstance(cash_resp, RedirectResponse)
    assert isinstance(partner_resp, RedirectResponse)
    assert "legacy" in (cash_resp.headers.get("location") or "")
    assert "legacy" in (partner_resp.headers.get("location") or "")

    db.refresh(cash)
    db.refresh(partner)
    assert cash.balance == 1000
    assert partner.balance == 8000


def test_production_complete_rejects_all_zero_materials(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda *args, **kwargs: None)
    user = User(username="admin", full_name="Admin", password_hash="x", role="admin", is_active=True)
    wh = Warehouse(name="Xom", code="WHX", is_active=True)
    out_wh = Warehouse(name="Tayyor", code="WHT", is_active=True)
    material = Product(code="M1", name="Shakar", type="xom", is_active=True, sale_price=1, purchase_price=2)
    finished = Product(code="F1", name="Holva", type="tayyor", is_active=True, sale_price=10, purchase_price=5)
    db.add_all([user, wh, out_wh, material, finished])
    db.flush()
    recipe = Recipe(name="Holva retsept", product_id=finished.id, output_quantity=1, is_active=True)
    db.add(recipe)
    db.flush()
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=2))
    db.add(Stock(warehouse_id=wh.id, product_id=material.id, quantity=100))
    db.add(Stock(warehouse_id=out_wh.id, product_id=finished.id, quantity=0))
    production = Production(
        number="PR-TEST-1",
        recipe_id=recipe.id,
        warehouse_id=wh.id,
        output_warehouse_id=out_wh.id,
        quantity=10,
        status="draft",
        date=datetime.now(),
        user_id=user.id,
        current_stage=1,
        max_stage=2,
    )
    db.add(production)
    db.flush()
    db.add(ProductionItem(production_id=production.id, product_id=material.id, quantity=0))
    db.commit()

    resp = run(main.complete_production(prod_id=production.id, db=db, current_user=user))
    assert isinstance(resp, RedirectResponse)
    location = unquote(resp.headers.get("location") or "")
    assert "no_materials" in location or "Xom ashyo miqdori 0" in location

    db.refresh(production)
    mat_stock = db.query(Stock).filter(Stock.warehouse_id == wh.id, Stock.product_id == material.id).one()
    fg_stock = db.query(Stock).filter(Stock.warehouse_id == out_wh.id, Stock.product_id == finished.id).one()
    assert production.status == "draft"
    assert mat_stock.quantity == 100
    assert fg_stock.quantity == 0
