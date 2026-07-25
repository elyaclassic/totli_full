"""Regression tests for newly found critical money/inventory bugs on main."""
import asyncio
import io
from types import SimpleNamespace

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import UploadFile, FormData
from starlette.requests import Request

import main
from app.models.database import (
    Base,
    CashRegister,
    Order,
    OrderItem,
    Partner,
    Payment,
    Product,
    Production,
    ProductionItem,
    Recipe,
    RecipeItem,
    Stock,
    StockAdjustmentDoc,
    StockAdjustmentDocItem,
    User,
    Warehouse,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def run(coro):
    return asyncio.run(coro)


def add_user(db, username="admin", role="admin"):
    user = User(username=username, password_hash="x", full_name=username, role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_product(db, code="P1", name="Product", ptype="tayyor"):
    product = Product(
        code=code,
        name=name,
        type=ptype,
        purchase_price=10,
        sale_price=20,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_warehouse(db, code="W1", name="Main"):
    warehouse = Warehouse(code=code, name=name, is_active=True)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def add_partner(db, code="C1", name="Customer", balance=0.0):
    partner = Partner(code=code, name=name, type="customer", balance=balance, is_active=True)
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def test_sales_confirm_rejects_duplicate_lines_that_oversell(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = add_user(db)
    warehouse = add_warehouse(db)
    product = add_product(db)
    partner = add_partner(db)
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=10))
    db.commit()

    order = Order(
        number="SALE-DUP-1",
        type="sale",
        partner_id=partner.id,
        warehouse_id=warehouse.id,
        user_id=user.id,
        status="draft",
        subtotal=280,
        total=280,
    )
    db.add(order)
    db.commit()
    db.add_all(
        [
            OrderItem(order_id=order.id, product_id=product.id, quantity=7, price=20, total=140),
            OrderItem(order_id=order.id, product_id=product.id, quantity=7, price=20, total=140),
        ]
    )
    db.commit()

    resp = run(main.sales_confirm(order.id, db=db, current_user=user))
    db.refresh(order)
    stock = db.query(Stock).filter(Stock.warehouse_id == warehouse.id, Stock.product_id == product.id).first()

    assert order.status == "draft"
    assert stock.quantity == 10
    assert "error=stock" in (resp.headers.get("location") or "")


def test_production_complete_rejects_duplicate_material_oversell(db, monkeypatch):
    monkeypatch.setattr(main, "check_low_stock_and_notify", lambda _db: None)
    user = add_user(db)
    warehouse = add_warehouse(db)
    material = add_product(db, code="M1", name="Flour", ptype="xomashyo")
    finished = add_product(db, code="F1", name="Halva", ptype="tayyor")
    db.add(Stock(warehouse_id=warehouse.id, product_id=material.id, quantity=10))
    db.commit()

    recipe = Recipe(
        name="R1",
        product_id=finished.id,
        output_quantity=1,
        is_active=True,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    db.add(RecipeItem(recipe_id=recipe.id, product_id=material.id, quantity=1))
    db.commit()

    production = Production(
        number="PR-DUP-1",
        recipe_id=recipe.id,
        warehouse_id=warehouse.id,
        output_warehouse_id=warehouse.id,
        quantity=1,
        status="draft",
        user_id=user.id,
    )
    db.add(production)
    db.commit()
    db.refresh(production)
    db.add_all(
        [
            ProductionItem(production_id=production.id, product_id=material.id, quantity=7),
            ProductionItem(production_id=production.id, product_id=material.id, quantity=7),
        ]
    )
    db.commit()

    resp = run(main.complete_production(production.id, db=db, current_user=user))
    db.refresh(production)
    stock = db.query(Stock).filter(Stock.warehouse_id == warehouse.id, Stock.product_id == material.id).first()

    assert production.status == "draft"
    assert stock.quantity == 10
    assert "error=insufficient_stock" in (resp.headers.get("location") or "")


def test_finance_payment_updates_cash_balance(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = add_user(db)
    cash = CashRegister(name="Main", balance=1000, is_active=True)
    db.add(cash)
    db.commit()
    db.refresh(cash)

    request = Request({"type": "http", "method": "POST", "path": "/finance/payment", "headers": []})
    resp = run(
        main.finance_payment(
            request,
            type="income",
            amount=250,
            cash_register_id=cash.id,
            description="Test income",
            db=db,
            current_user=user,
        )
    )
    db.refresh(cash)
    payment = db.query(Payment).order_by(Payment.id.desc()).first()

    assert resp.status_code == 303
    assert "/finance" in (resp.headers.get("location") or "")
    assert cash.balance == 1250
    assert payment is not None
    assert payment.type == "income"
    assert payment.amount == 250

    resp = run(
        main.finance_payment(
            request,
            type="expense",
            amount=300,
            cash_register_id=cash.id,
            description="Test expense",
            db=db,
            current_user=user,
        )
    )
    db.refresh(cash)
    assert cash.balance == 950
    assert resp.status_code == 303

    resp = run(
        main.finance_payment(
            request,
            type="expense",
            amount=5000,
            cash_register_id=cash.id,
            description="Too much",
            db=db,
            current_user=user,
        )
    )
    db.refresh(cash)
    assert cash.balance == 950
    assert "error=payment" in (resp.headers.get("location") or "")


async def _form_request(file_bytes: bytes, filename: str = "stock.xlsx"):
    upload = UploadFile(filename=filename, file=io.BytesIO(file_bytes))
    form = FormData([("file", upload)])

    async def form_fn():
        return form

    request = SimpleNamespace(form=form_fn)
    return request


def _xlsx_bytes(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Ombor", "Mahsulot", "Miqdor", "Tannarx", "Sotuv"])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_warehouse_excel_import_merges_duplicate_product_rows(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = add_user(db)
    warehouse = add_warehouse(db, code="WH1", name="Asosiy")
    product = add_product(db, code="SKU1", name="Halva")
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=50))
    db.commit()

    content = _xlsx_bytes(
        [
            ["Asosiy", "SKU1", 80, 0, 0],
            ["Asosiy", "SKU1", 20, 0, 0],  # last wins; must not leave stock at 20 after first set+second set with wrong delta
        ]
    )
    request = run(_form_request(content))
    resp = run(main.warehouse_import(request, db=db, current_user=user))
    stock = db.query(Stock).filter(Stock.warehouse_id == warehouse.id, Stock.product_id == product.id).first()
    doc = db.query(StockAdjustmentDoc).order_by(StockAdjustmentDoc.id.desc()).first()
    items = db.query(StockAdjustmentDocItem).filter(StockAdjustmentDocItem.doc_id == doc.id).all()

    assert resp.status_code == 303
    assert "success=import" in (resp.headers.get("location") or "")
    assert len(items) == 1
    assert items[0].quantity == 20
    assert stock.quantity == 20
