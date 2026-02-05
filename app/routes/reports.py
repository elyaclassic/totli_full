"""
Hisobotlar — savdo, qoldiq, qarzdorlik va Excel export.
"""
import io
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from app.core import templates
from app.models.database import get_db, Order, Stock, Product, Partner, Warehouse, User
from app.deps import get_current_user, require_auth

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_class=HTMLResponse)
async def reports_index(request: Request):
    """Hisobotlar bosh sahifasi"""
    return templates.TemplateResponse("reports/index.html", {
        "request": request,
        "page_title": "Hisobotlar",
    })


@router.get("/sales", response_class=HTMLResponse)
async def report_sales(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    orders = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= start_date,
        Order.date <= end_date + " 23:59:59",
    ).all()
    total = sum(o.total for o in orders)
    return templates.TemplateResponse("reports/sales.html", {
        "request": request,
        "orders": orders,
        "total": total,
        "start_date": start_date,
        "end_date": end_date,
        "page_title": "Savdo hisoboti",
    })


@router.get("/sales/export")
async def report_sales_export(
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    orders = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= start_date,
        Order.date <= end_date + " 23:59:59",
    ).order_by(Order.date.desc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Savdo"
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    ws["A1"] = "Savdo hisoboti"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Davr: {start_date} — {end_date}"
    ws.append(["№", "Sana", "Buyurtma", "Mijoz", "Jami", "Holat"])
    for c in range(1, 7):
        ws.cell(row=4, column=c).fill = header_fill
        ws.cell(row=4, column=c).font = Font(bold=True, color="FFFFFF")
    for i, o in enumerate(orders, 1):
        ws.append([
            i,
            o.date.strftime("%d.%m.%Y %H:%M") if o.date else "",
            o.number or "",
            o.partner.name if o.partner else "",
            float(o.total or 0),
            o.status or "",
        ])
    total = sum(o.total or 0 for o in orders)
    ws.append(["", "", "", "JAMI:", total, ""])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=savdo_{start_date}_{end_date}.xlsx"},
    )


@router.get("/stock", response_class=HTMLResponse)
async def report_stock(request: Request, db: Session = Depends(get_db)):
    stocks = db.query(Stock).join(Product).all()
    return templates.TemplateResponse("reports/stock.html", {
        "request": request,
        "stocks": stocks,
        "page_title": "Qoldiq hisoboti",
    })


@router.get("/stock/export")
async def report_stock_export(db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    stocks = (
        db.query(Stock)
        .join(Product, Stock.product_id == Product.id)
        .join(Warehouse, Stock.warehouse_id == Warehouse.id)
        .order_by(Warehouse.name, Product.name)
        .all()
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Qoldiq"
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    ws["A1"] = "Qoldiq hisoboti"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    ws.append(["Ombor", "Mahsulot", "Kod", "Qoldiq", "Minimal", "Narx", "Summa"])
    for c in range(1, 8):
        ws.cell(row=4, column=c).fill = header_fill
        ws.cell(row=4, column=c).font = Font(bold=True, color="FFFFFF")
    for s in stocks:
        p = s.product
        wh = s.warehouse
        min_s = getattr(p, "min_stock", 0) or 0
        price = getattr(p, "purchase_price", 0) or 0
        ws.append([
            wh.name if wh else "",
            p.name if p else "",
            (p.barcode or p.code or "") if p else "",
            float(s.quantity or 0),
            float(min_s),
            float(price),
            float((s.quantity or 0) * price),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=qoldiq_{datetime.now().strftime('%Y%m%d')}.xlsx"},
    )


@router.get("/debts", response_class=HTMLResponse)
async def report_debts(request: Request, db: Session = Depends(get_db)):
    debtors = db.query(Partner).filter(Partner.balance != 0).all()
    total_debt = sum(p.balance for p in debtors if p.balance > 0)
    total_credit = sum(abs(p.balance) for p in debtors if p.balance < 0)
    return templates.TemplateResponse("reports/debts.html", {
        "request": request,
        "debtors": debtors,
        "total_debt": total_debt,
        "total_credit": total_credit,
        "page_title": "Qarzdorlik hisoboti",
    })


@router.get("/debts/export")
async def report_debts_export(db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    debtors = db.query(Partner).filter(Partner.balance != 0).order_by(Partner.name).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Qarzdorlik"
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    ws["A1"] = "Qarzdorlik hisoboti"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    ws.append(["Kod", "Mijoz", "Telefon", "Balans (qarz +)", "Kredit limiti"])
    for c in range(1, 6):
        ws.cell(row=4, column=c).fill = header_fill
        ws.cell(row=4, column=c).font = Font(bold=True, color="FFFFFF")
    for p in debtors:
        ws.append([
            p.code or "",
            p.name or "",
            p.phone or "",
            float(p.balance or 0),
            float(p.credit_limit or 0),
        ])
    total = sum(p.balance for p in debtors if (p.balance or 0) > 0)
    ws.append(["", "", "JAMI QARZ:", total, ""])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=qarzdorlik_{datetime.now().strftime('%Y%m%d')}.xlsx"},
    )
