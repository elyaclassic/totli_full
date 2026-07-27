"""Regression tests for transfer invent, partner hard-delete, reports stock import."""
import asyncio
import io
from datetime import datetime

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import UploadFile
from starlette.responses import Response

import main
from app.models.database import (
    Base,
    Partner,
    PartnerBalanceDoc,
    PartnerBalanceDocItem,
    Product,
    Stock,
    StockMovement,
    User,
    Warehouse,
    WarehouseTransfer,
    WarehouseTransferItem,
)
from app.routes import reports as reports_routes


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


def add_product(db, code="P1", name="Product"):
    product = Product(
        code=code,
        name=name,
        type="tayyor",
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


def test_transfer_confirm_rejects_duplicate_lines_that_invent_stock(db, monkeypatch):
    monkeypatch.setattr(main, "log_audit", lambda *args, **kwargs: None)
    user = add_user(db)
    src = add_warehouse(db, code="SRC", name="Source")
    dst = add_warehouse(db, code="DST", name="Dest")
    product = add_product(db)
    db.add(Stock(warehouse_id=src.id, product_id=product.id, quantity=10))
    db.commit()

    transfer = WarehouseTransfer(
        number="OT-DUP-1",
        from_warehouse_id=src.id,
        to_warehouse_id=dst.id,
        status="pending_approval",
        user_id=user.id,
        date=datetime.now(),
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    db.add_all(
        [
            WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=7),
            WarehouseTransferItem(transfer_id=transfer.id, product_id=product.id, quantity=7),
        ]
    )
    db.commit()

    resp = run(main.warehouse_transfer_confirm(transfer.id, db=db, current_user=user))
    db.refresh(transfer)
    src_stock = db.query(Stock).filter(Stock.warehouse_id == src.id, Stock.product_id == product.id).first()
    dst_stock = db.query(Stock).filter(Stock.warehouse_id == dst.id, Stock.product_id == product.id).first()

    assert transfer.status == "pending_approval"
    assert src_stock.quantity == 10
    assert dst_stock is None or (dst_stock.quantity or 0) == 0
    from urllib.parse import unquote
    assert "yetarli emas" in unquote(resp.headers.get("location") or "")


def test_partner_delete_soft_deletes_and_blocks_balance(db):
    user = add_user(db)
    partner = Partner(
        code="C-BAL",
        name="Debtor",
        type="customer",
        balance=1000.0,
        is_active=True,
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)

    with pytest.raises(Exception) as excinfo:
        run(main.partner_delete(partner.id, db=db, current_user=user))
    assert "balans" in str(excinfo.value.detail).lower() or getattr(excinfo.value, "status_code", None) == 400
    db.refresh(partner)
    assert partner.is_active is True
    assert db.query(Partner).filter(Partner.id == partner.id).first() is not None

    partner.balance = 0
    db.commit()
    resp = run(main.partner_delete(partner.id, db=db, current_user=user))
    db.refresh(partner)
    assert partner.is_active is False
    assert db.query(Partner).filter(Partner.id == partner.id).first() is not None
    assert isinstance(resp, Response)


def test_partner_delete_blocks_balance_doc_history(db):
    user = add_user(db)
    partner = Partner(code="C-DOC", name="WithDoc", type="customer", balance=0.0, is_active=True)
    db.add(partner)
    db.commit()
    db.refresh(partner)
    doc = PartnerBalanceDoc(
        number="KB-1",
        date=datetime.now(),
        user_id=user.id,
        status="confirmed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.add(PartnerBalanceDocItem(doc_id=doc.id, partner_id=partner.id, balance=0, previous_balance=0))
    db.commit()

    with pytest.raises(Exception) as excinfo:
        run(main.partner_delete(partner.id, db=db, current_user=user))
    assert getattr(excinfo.value, "status_code", None) == 400
    db.refresh(partner)
    assert partner.is_active is True


def test_reports_stock_import_merges_duplicate_absolute_rows(db):
    user = add_user(db)
    warehouse = add_warehouse(db, code="WH1", name="Ombor")
    product = add_product(db, code="SKU1", name="Yong'oq")
    db.add(Stock(warehouse_id=warehouse.id, product_id=product.id, quantity=100))
    db.commit()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Ombor", "Mahsulot", "Qoldiq"])
    ws.append([warehouse.name, product.code, 80])
    ws.append([warehouse.name, product.code, 20])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    upload = UploadFile(filename="stock.xlsx", file=buf)

    resp = run(reports_routes.report_stock_import(file=upload, db=db, current_user=user))
    stock = db.query(Stock).filter(Stock.warehouse_id == warehouse.id, Stock.product_id == product.id).first()
    movements = db.query(StockMovement).filter(
        StockMovement.warehouse_id == warehouse.id,
        StockMovement.product_id == product.id,
        StockMovement.document_type == "ReportStockImport",
    ).all()

    assert stock.quantity == 20
    assert len(movements) == 1
    assert movements[0].quantity_change == -80
    assert isinstance(resp, Response)
