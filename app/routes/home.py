"""
Bosh sahifa va /info redirect.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core import templates
from app.models.database import (
    get_db, User, Product, Partner, Order, Stock,
    CashRegister, Employee,
)
from app.deps import get_current_user, require_auth

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Bosh sahifa - Dashboard"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    error = request.query_params.get("error")
    try:
        stats = {
            "tayyor_count": db.query(Product).filter(Product.type == "tayyor").count(),
            "yarim_tayyor_count": db.query(Product).filter(Product.type == "yarim_tayyor").count(),
            "hom_ashyo_count": db.query(Product).filter(Product.type == "hom_ashyo").count(),
            "partners_count": db.query(Partner).count(),
            "employees_count": db.query(Employee).count(),
            "products_count": db.query(Product).filter(Product.is_active == True).count(),
            "materials_count": db.query(Product).filter(Product.type == "hom_ashyo", Product.is_active == True).count(),
        }
        today = datetime.now().date()
        today_sales = db.query(Order).filter(Order.type == "sale", Order.date >= today).all()
        stats["today_sales"] = sum(s.total for s in today_sales)
        stats["today_orders"] = len(today_sales)
        cash = db.query(CashRegister).first()
        stats["cash_balance"] = cash.balance if cash else 0
        debtors = db.query(Partner).filter(Partner.balance > 0).all()
        stats["total_debt"] = sum(p.balance for p in debtors)
        recent_sales = (
            db.query(Order)
            .filter(Order.type == "sale")
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )
        low_stock_count = db.query(Stock).join(Product).filter(Stock.quantity < Product.min_stock).count()
        birthday_today_count = 0
        if hasattr(Employee, "birth_date"):
            try:
                md = today.strftime("%m-%d")
                for e in db.query(Employee).filter(Employee.birth_date.isnot(None), Employee.is_active == True).all():
                    if e.birth_date and e.birth_date.strftime("%m-%d") == md:
                        birthday_today_count += 1
            except Exception:
                pass
        overdue_cutoff = datetime.now() - timedelta(days=7)
        overdue_debts_count = db.query(Order).filter(
            Order.type == "sale",
            Order.debt > 0,
            Order.created_at < overdue_cutoff,
        ).count()
    except Exception as e:
        stats = {
            "tayyor_count": 0, "yarim_tayyor_count": 0, "hom_ashyo_count": 0,
            "partners_count": 0, "employees_count": 0, "products_count": 0, "materials_count": 0,
            "today_sales": 0, "today_orders": 0, "cash_balance": 0, "total_debt": 0,
        }
        recent_sales = []
        low_stock_count = 0
        birthday_today_count = 0
        overdue_debts_count = 0
        if not error:
            error = "Statistika yuklanmadi"
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "current_user": current_user,
        "page_title": "Bosh sahifa",
        "error": error,
        "recent_sales": recent_sales,
        "low_stock_count": low_stock_count,
        "birthday_today_count": birthday_today_count,
        "overdue_debts_count": overdue_debts_count,
    })


@router.get("/info")
async def info_index(request: Request, current_user: User = Depends(require_auth)):
    """Ma'lumotlar - /info/units ga yo'naltirish"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/info/units", status_code=303)
