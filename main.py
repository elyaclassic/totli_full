
# --- Barcha importlar ---

from fastapi import FastAPI, Request, Depends, HTTPException, Form, Cookie, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uvicorn
import barcode
from barcode.writer import ImageWriter
from PIL import Image
import os
from typing import Optional
import openpyxl
import io
from app.models.database import (
    get_db, init_db, 
    User, Product, Category, Unit, Warehouse, Stock,
    Partner, Order, OrderItem, Payment, CashRegister,
    Recipe, RecipeItem, Production, Employee, Salary,
    Agent, AgentLocation, Route, RoutePoint, Visit,
    Driver, DriverLocation, Delivery, PartnerLocation,
    Purchase, PurchaseItem, Department, Direction, Region
)
from app.utils.auth import (
    hash_password, verify_password, 
    create_session_token, get_user_from_token
)

app = FastAPI(title="TOTLI HOLVA", description="Biznes boshqaruv tizimi", version="1.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ==========================================
# AUTENTIFIKATSIYA HELPER FUNKSIYALARI
# ==========================================

def get_current_user(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Cookie dan foydalanuvchini olish"""
    if not session_token:
        return None
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return None
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return None
    
    return user


def require_auth(current_user: User = Depends(get_current_user)) -> Optional[User]:
    """Login talab qilish - None qaytaradi agar login qilmagan bo'lsa"""
    return current_user


# ==========================================
# AUTENTIFIKATSIYA ENDPOINTLARI
# ==========================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, current_user: User = Depends(get_current_user)):
    """Login sahifasi"""
    # Agar foydalanuvchi allaqachon tizimga kirgan bo'lsa, bosh sahifaga yo'naltirish
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login qilish"""
    try:
        # Foydalanuvchini topish
        user = db.query(User).filter(User.username == username).first()
        
        # Parolni tekshirish
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Login yoki parol noto'g'ri!"
            })
        
        # Faol emasligini tekshirish
        if not user.is_active:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Sizning hisobingiz faol emas. Administrator bilan bog'laning."
            })
        
        # Session token yaratish
        token = create_session_token(user.id, user.username)
        print(f"✅ Token yaratildi: {token[:50]}...")
        
        # Cookie o'rnatish
        redirect_response = RedirectResponse(url="/", status_code=303)
        redirect_response.set_cookie(
            key="session_token",
            value=token,
            path="/",
            httponly=True,
            max_age=86400,  # 24 soat
            samesite="lax",
            secure=False  # HTTP uchun False bo'lishi kerak
        )
        print(f"✅ Cookie o'rnatildi. Redirect: /")
        
        return redirect_response
    
    except Exception as e:
        print(f"❌ LOGIN XATO: {str(e)}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Tizimda xatolik yuz berdi: {str(e)}"
        })


@app.get("/logout")
async def logout():
    """Logout qilish"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response


# ==========================================
# DASHBOARDS
# ==========================================

# Test route without authentication
@app.get("/test/dashboard/executive", response_class=HTMLResponse)
async def executive_dashboard_test(request: Request, db: Session = Depends(get_db)):
    """Rahbariyat Dashboard - Test (fake data)"""
    
    # Fake user for testing
    fake_user = {"username": "test", "role": "admin"}
    
    # Fake statistika
    stats = {
        'today_sales': 5500000,
        'sales_growth': 12.5,
        'today_orders': 45,
        'completed_orders': 38,
        'active_agents': 12,
        'total_agents': 15,
        'warehouse_value': 25000000,
        'low_stock_count': 3
    }
    
    # Fake 7 kunlik savdo
    sales_trend = {
        "labels": ["26.01", "27.01", "28.01", "29.01", "30.01", "31.01", "01.02"],
        "data": [4200000, 4500000, 4800000, 5100000, 5300000, 5200000, 5500000]
    }
    
    # Fake top mahsulotlar
    top_products = {
        "labels": ["Shokolad tort", "Medovik", "Napoleon", "Tiramisu", "Eclair"],
        "data": [150, 120, 100, 85, 70]
    }
    
    # Fake top agentlar
    top_agents = [
        {'name': 'Alisher Karimov', 'sales': 1200000, 'orders': 25},
        {'name': 'Dilshod Rahimov', 'sales': 980000, 'orders': 20},
        {'name': 'Sardor Usmonov', 'sales': 850000, 'orders': 18},
        {'name': 'Jasur Toshmatov', 'sales': 720000, 'orders': 15},
        {'name': 'Bobur Sharipov', 'sales': 650000, 'orders': 12}
    ]
    
    # Fake ogohlantirishlar
    alerts = [
        {
            'title': 'Past qoldiq',
            'message': '3 ta mahsulot qoldig\'i past darajada'
        },
        {
            'title': 'Yangi buyurtma',
            'message': 'Toshkent filialidan yangi buyurtma keldi'
        }
    ]
    
    return templates.TemplateResponse("dashboards/executive.html", {
        "request": request,
        "page_title": "Rahbariyat Dashboard",
        "user": fake_user,
        "stats": stats,
        "sales_trend": sales_trend,
        "top_products": top_products,
        "top_agents": top_agents,
        "alerts": alerts
    })


@app.get("/dashboard/executive", response_class=HTMLResponse)
async def executive_dashboard(request: Request, db: Session = Depends(get_db)):
    """Rahbariyat Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Order, OrderItem, Agent, Stock, Product
    
    # Get user from session cookie
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return RedirectResponse(url="/login", status_code=303)
    
    # Bugungi sana
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    # Bugungi savdo (completed orders)
    today_sales = db.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == today,
        Order.status == 'completed'
    ).scalar() or 0
    
    # Kechagi savdo
    yesterday_sales = db.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == yesterday,
        Order.status == 'completed'
    ).scalar() or 0
    
    # O'sish foizi
    sales_growth = 0
    if yesterday_sales > 0:
        sales_growth = ((today_sales - yesterday_sales) / yesterday_sales) * 100
    
    # Bugungi buyurtmalar
    today_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0
    
    # Bajarilgan buyurtmalar
    completed_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today,
        Order.status == 'completed'
    ).scalar() or 0
    
    # Faol agentlar
    active_agents = db.query(func.count(Agent.id)).filter(
        Agent.is_active == True
    ).scalar() or 0
    
    # Jami agentlar
    total_agents = db.query(func.count(Agent.id)).scalar() or 0
    
    # Ombor qiymati
    warehouse_value = db.query(
        func.sum(Stock.quantity * Product.cost_price)
    ).join(
        Product, Stock.product_id == Product.id
    ).scalar() or 0
    
    # Past qoldiq mahsulotlar
    low_stock_count = db.query(func.count(Stock.id)).filter(
        Stock.quantity < 10
    ).scalar() or 0
    
    # 7 kunlik savdo dinamikasi
    sales_trend_labels = []
    sales_trend_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        sales = db.query(func.sum(Order.total)).filter(
            func.date(Order.created_at) == date,
            Order.status == 'completed'
        ).scalar() or 0
        sales_trend_labels.append(date.strftime('%d.%m'))
        sales_trend_data.append(float(sales))
    
    # Top 5 mahsulotlar
    top_products_query = db.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_qty')
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        func.date(Order.created_at) >= week_ago,
        Order.status == 'completed'
    ).group_by(Product.id, Product.name).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(5).all()
    
    top_products_labels = [p.name for p in top_products_query] or ['Ma\'lumot yo\'q']
    top_products_data = [float(p.total_qty) for p in top_products_query] or [0]
    
    # Top 5 agentlar
    top_agents_query = db.query(
        Agent.name,
        func.sum(Order.total).label('total_sales'),
        func.count(Order.id).label('order_count')
    ).join(
        Order, Agent.id == Order.partner_id  # Assuming agent is partner
    ).filter(
        func.date(Order.created_at) >= week_ago,
        Order.status == 'completed'
    ).group_by(Agent.id, Agent.name).order_by(
        func.sum(Order.total).desc()
    ).limit(5).all()
    
    top_agents = [
        {
            'name': a.name,
            'sales': float(a.total_sales or 0),
            'orders': a.order_count
        }
        for a in top_agents_query
    ] or [{'name': 'Ma\'lumot yo\'q', 'sales': 0, 'orders': 0}]
    
    # Ogohlantirishlar
    alerts = []
    
    # Past qoldiq ogohlantirishlari
    if low_stock_count > 0:
        alerts.append({
            'title': 'Past qoldiq',
            'message': f'{low_stock_count} ta mahsulot qoldig\'i past darajada'
        })
    
    # Bugungi savdo past bo'lsa
    if yesterday_sales > 0 and sales_growth < -10:
        alerts.append({
            'title': 'Savdo pasaygan',
            'message': f'Bugungi savdo kechaga nisbatan {abs(sales_growth):.1f}% kamaygan'
        })
    
    # Statistika
    stats = {
        'today_sales': float(today_sales),
        'sales_growth': round(sales_growth, 1),
        'today_orders': today_orders,
        'completed_orders': completed_orders,
        'active_agents': active_agents,
        'total_agents': total_agents,
        'warehouse_value': float(warehouse_value),
        'low_stock_count': low_stock_count
    }
    
    return templates.TemplateResponse("dashboards/executive.html", {
        "request": request,
        "page_title": "Rahbariyat Dashboard",
        "user": user,
        "stats": stats,
        "sales_trend": {
            "labels": sales_trend_labels,
            "data": sales_trend_data
        },
        "top_products": {
            "labels": top_products_labels,
            "data": top_products_data
        },
        "top_agents": top_agents,
        "alerts": alerts
    })


# Sales Dashboard - Real Data
@app.get("/dashboard/sales", response_class=HTMLResponse)
async def sales_dashboard(request: Request, db: Session = Depends(get_db)):
    """Savdo Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Order, Partner
    
    # Get user from session cookie
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return RedirectResponse(url="/login", status_code=303)
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's sales
    today_sales = db.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == today,
        Order.status == 'completed'
    ).scalar() or 0
    
    yesterday_sales = db.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == yesterday,
        Order.status == 'completed'
    ).scalar() or 0
    
    sales_growth = 0
    if yesterday_sales > 0:
        sales_growth = ((today_sales - yesterday_sales) / yesterday_sales) * 100
    
    # Orders
    total_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0
    
    completed_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today,
        Order.status == 'completed'
    ).scalar() or 0
    
    # Customers
    active_customers = db.query(func.count(func.distinct(Order.partner_id))).filter(
        func.date(Order.created_at) >= month_ago
    ).scalar() or 0
    
    new_customers = db.query(func.count(func.distinct(Order.partner_id))).filter(
        func.date(Order.created_at) >= week_ago
    ).scalar() or 0
    
    # Average check
    avg_check = today_sales / total_orders if total_orders > 0 else 0
    
    metrics = {
        'today_sales': float(today_sales),
        'sales_growth': round(sales_growth, 1),
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'active_customers': active_customers,
        'new_customers': new_customers,
        'avg_check': float(avg_check)
    }
    
    # Order Status
    status_counts = db.query(
        Order.status,
        func.count(Order.id)
    ).filter(
        func.date(Order.created_at) >= week_ago
    ).group_by(Order.status).all()
    
    status_map = {'draft': 'Yangi', 'confirmed': 'Jarayonda', 'completed': 'Bajarilgan', 'cancelled': 'Bekor qilingan'}
    order_status = {
        "labels": [status_map.get(s[0], s[0]) for s in status_counts] or ['Ma\'lumot yo\'q'],
        "data": [s[1] for s in status_counts] or [0]
    }
    
    # Weekly Sales
    weekly_labels = []
    weekly_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        sales = db.query(func.sum(Order.total)).filter(
            func.date(Order.created_at) == date,
            Order.status == 'completed'
        ).scalar() or 0
        weekly_labels.append(['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Juma', 'Shan'][date.weekday()])
        weekly_data.append(float(sales))
    
    weekly_sales = {"labels": weekly_labels, "data": weekly_data}
    
    # Recent Orders
    recent = db.query(Order, Partner.name).join(
        Partner, Order.partner_id == Partner.id, isouter=True
    ).filter(
        func.date(Order.created_at) >= week_ago
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    status_text_map = {'draft': 'Yangi', 'confirmed': 'Jarayonda', 'completed': 'Bajarilgan', 'cancelled': 'Bekor qilingan'}
    recent_orders = [
        {
            'number': o.number,
            'customer': p_name or 'Noma\'lum',
            'total': float(o.total),
            'status': o.status,
            'status_text': status_text_map.get(o.status, o.status)
        }
        for o, p_name in recent
    ] or [{'number': '-', 'customer': 'Ma\'lumot yo\'q', 'total': 0, 'status': 'draft', 'status_text': '-'}]
    
    # Top Customers
    top = db.query(
        Partner.name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total).label('total_sales')
    ).join(
        Order, Partner.id == Order.partner_id
    ).filter(
        func.date(Order.created_at) >= month_ago,
        Order.status == 'completed'
    ).group_by(Partner.id, Partner.name).order_by(
        func.sum(Order.total).desc()
    ).limit(5).all()
    
    top_customers = [
        {'name': t.name, 'orders': t.order_count, 'total': float(t.total_sales)}
        for t in top
    ] or [{'name': 'Ma\'lumot yo\'q', 'orders': 0, 'total': 0}]
    
    # Fake funnel (not in database yet)
    funnel = {
        "labels": ["Tashrif", "Qiziqish", "Taklif", "Buyurtma", "To'lov"],
        "data": [250, 180, 120, total_orders, completed_orders]
    }
    
    return templates.TemplateResponse("dashboards/sales.html", {
        "request": request,
        "page_title": "Savdo Dashboard",
        "user": user,
        "metrics": metrics,
        "order_status": order_status,
        "funnel": funnel,
        "weekly_sales": weekly_sales,
        "recent_orders": recent_orders,
        "top_customers": top_customers
    })


# Sales Dashboard - Test (fake data)
@app.get("/test/dashboard/sales", response_class=HTMLResponse)
async def sales_dashboard_test(request: Request, db: Session = Depends(get_db)):
    """Savdo Dashboard - Test (fake data)"""
    
    # Fake user
    fake_user = {"username": "test", "role": "sales"}
    
    # Metrics
    metrics = {
        'today_sales': 5500000,
        'sales_growth': 15.3,
        'total_orders': 45,
        'completed_orders': 38,
        'active_customers': 128,
        'new_customers': 12,
        'avg_check': 122222
    }
    
    # Order Status
    order_status = {
        "labels": ["Yangi", "Jarayonda", "Bajarilgan", "Bekor qilingan"],
        "data": [7, 12, 38, 3]
    }
    
    # Sales Funnel
    funnel = {
        "labels": ["Tashrif", "Qiziqish", "Taklif", "Buyurtma", "To'lov"],
        "data": [250, 180, 120, 60, 45]
    }
    
    # Weekly Sales
    weekly_sales = {
        "labels": ["Dush", "Sesh", "Chor", "Pay", "Juma", "Shan", "Yak"],
        "data": [720000, 850000, 920000, 880000, 1100000, 950000, 780000]
    }
    
    # Recent Orders
    recent_orders = [
        {'number': 'ORD-1234', 'customer': 'Anvar Toshmatov', 'total': 450000, 'status': 'completed', 'status_text': 'Bajarilgan'},
        {'number': 'ORD-1235', 'customer': 'Dilshod Karimov', 'total': 320000, 'status': 'processing', 'status_text': 'Jarayonda'},
        {'number': 'ORD-1236', 'customer': 'Sardor Usmonov', 'total': 180000, 'status': 'new', 'status_text': 'Yangi'},
        {'number': 'ORD-1237', 'customer': 'Jasur Rahimov', 'total': 520000, 'status': 'completed', 'status_text': 'Bajarilgan'},
        {'number': 'ORD-1238', 'customer': 'Bobur Sharipov', 'total': 280000, 'status': 'processing', 'status_text': 'Jarayonda'}
    ]
    
    # Top Customers
    top_customers = [
        {'name': 'Anvar Toshmatov', 'orders': 45, 'total': 5200000},
        {'name': 'Dilshod Karimov', 'orders': 38, 'total': 4100000},
        {'name': 'Sardor Usmonov', 'orders': 32, 'total': 3500000},
        {'name': 'Jasur Rahimov', 'orders': 28, 'total': 2900000},
        {'name': 'Bobur Sharipov', 'orders': 25, 'total': 2400000}
    ]
    
    return templates.TemplateResponse("dashboards/sales.html", {
        "request": request,
        "page_title": "Savdo Dashboard",
        "user": fake_user,
        "metrics": metrics,
        "order_status": order_status,
        "funnel": funnel,
        "weekly_sales": weekly_sales,
        "recent_orders": recent_orders,
        "top_customers": top_customers
    })


# Agent Dashboard - Real Data
@app.get("/dashboard/agent", response_class=HTMLResponse)
async def agent_dashboard(request: Request, db: Session = Depends(get_db)):
    """Agent Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Agent, Visit, Route, RoutePoint, Partner, Order, AgentLocation
    
    # Get user from session cookie
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return RedirectResponse(url="/login", status_code=303)
    
    # Get agent for current user (assuming user has agent_id or we use first agent)
    agent = db.query(Agent).filter(Agent.is_active == True).first()
    if not agent:
        # No agent found - show empty dashboard
        agent = {'name': 'Agent topilmadi', 'location': '-'}
        return templates.TemplateResponse("dashboards/agent.html", {
            "request": request,
            "page_title": "Agent Dashboard",
            "user": user,
            "agent": agent,
            "kpi": {'visits_completed': 0, 'visits_total': 0, 'visits_percent': 0, 'today_sales': 0, 'orders': 0, 'orders_completed': 0, 'target_achieved': 0, 'target_total': 25000000, 'target_percent': 0},
            "schedule": [],
            "recent_orders": [],
            "customers": [],
            "performance": {'labels': [], 'sales': [], 'target': []}
        })
    
    today = datetime.now().date()
    month_ago = today - timedelta(days=30)
    
    # Agent info with location
    latest_location = db.query(AgentLocation).filter(
        AgentLocation.agent_id == agent.id
    ).order_by(AgentLocation.recorded_at.desc()).first()
    
    agent_info = {
        'name': agent.full_name,
        'location': latest_location.address if latest_location and latest_location.address else agent.region or 'Noma\'lum'
    }
    
    # Today's visits
    today_visits = db.query(func.count(Visit.id)).filter(
        Visit.agent_id == agent.id,
        func.date(Visit.visit_date) == today
    ).scalar() or 0
    
    completed_visits = db.query(func.count(Visit.id)).filter(
        Visit.agent_id == agent.id,
        func.date(Visit.visit_date) == today,
        Visit.status == 'visited'
    ).scalar() or 0
    
    visits_percent = int((completed_visits / today_visits * 100)) if today_visits > 0 else 0
    
    # Today's sales (orders created by agent)
    today_sales = db.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == today,
        Order.status == 'completed'
    ).scalar() or 0
    
    today_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0
    
    completed_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today,
        Order.status == 'completed'
    ).scalar() or 0
    
    # Monthly target (placeholder)
    target_total = 25000000
    month_sales = db.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) >= month_ago,
        Order.status == 'completed'
    ).scalar() or 0
    
    target_percent = int((month_sales / target_total * 100)) if target_total > 0 else 0
    
    kpi = {
        'visits_completed': completed_visits,
        'visits_total': today_visits,
        'visits_percent': visits_percent,
        'today_sales': float(today_sales),
        'orders': today_orders,
        'orders_completed': completed_orders,
        'target_achieved': float(month_sales),
        'target_total': target_total,
        'target_percent': target_percent
    }
    
    # Today's schedule from visits
    schedule_visits = db.query(Visit, Partner).join(
        Partner, Visit.partner_id == Partner.id
    ).filter(
        Visit.agent_id == agent.id,
        func.date(Visit.visit_date) == today
    ).order_by(Visit.check_in_time).all()
    
    schedule = []
    for visit, partner in schedule_visits:
        schedule.append({
            'customer': partner.name,
            'time': visit.check_in_time.strftime('%H:%M') if visit.check_in_time else '-',
            'address': partner.address or '-',
            'completed': visit.status == 'visited'
        })
    
    if not schedule:
        schedule = [{'customer': 'Bugun tashrif rejalashtirilmagan', 'time': '-', 'address': '-', 'completed': False}]
    
    # Recent orders
    recent = db.query(Order, Partner).join(
        Partner, Order.partner_id == Partner.id
    ).filter(
        func.date(Order.created_at) >= today - timedelta(days=7)
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    status_map = {'draft': ('Yangi', 'primary'), 'confirmed': ('Jarayonda', 'warning'), 'completed': ('Bajarilgan', 'success'), 'cancelled': ('Bekor qilingan', 'danger')}
    recent_orders = []
    for order, partner in recent:
        status_text, status_color = status_map.get(order.status, ('Noma\'lum', 'secondary'))
        recent_orders.append({
            'number': order.number,
            'customer': partner.name,
            'total': float(order.total),
            'status_color': status_color,
            'status_text': status_text
        })
    
    if not recent_orders:
        recent_orders = [{'number': '-', 'customer': 'Ma\'lumot yo\'q', 'total': 0, 'status_color': 'secondary', 'status_text': '-'}]
    
    # My customers (partners with recent orders)
    customers_query = db.query(
        Partner,
        func.max(Order.total).label('last_order')
    ).join(
        Order, Partner.id == Order.partner_id
    ).filter(
        func.date(Order.created_at) >= month_ago
    ).group_by(Partner.id).order_by(func.max(Order.created_at).desc()).limit(5).all()
    
    customers = []
    for partner, last_order in customers_query:
        customers.append({
            'name': partner.name,
            'phone': partner.phone or '-',
            'address': partner.address or '-',
            'last_order': float(last_order) if last_order else 0
        })
    
    if not customers:
        customers = [{'name': 'Ma\'lumot yo\'q', 'phone': '-', 'address': '-', 'last_order': 0}]
    
    # 30-day performance
    performance_labels = []
    performance_sales = []
    performance_target = []
    
    daily_target = target_total / 30
    cumulative_sales = 0
    
    for i in range(0, 30, 5):
        date = month_ago + timedelta(days=i)
        sales = db.query(func.sum(Order.total)).filter(
            func.date(Order.created_at) >= month_ago,
            func.date(Order.created_at) <= date,
            Order.status == 'completed'
        ).scalar() or 0
        
        cumulative_sales = float(sales)
        performance_labels.append(f'{i+1}-kun')
        performance_sales.append(cumulative_sales)
        performance_target.append(daily_target * (i + 1))
    
    performance = {
        'labels': performance_labels,
        'sales': performance_sales,
        'target': performance_target
    }
    
    return templates.TemplateResponse("dashboards/agent.html", {
        "request": request,
        "page_title": "Agent Dashboard",
        "user": user,
        "agent": agent_info,
        "kpi": kpi,
        "schedule": schedule,
        "recent_orders": recent_orders,
        "customers": customers,
        "performance": performance
    })


# Agent Dashboard - Test (fake data)
@app.get("/test/dashboard/agent", response_class=HTMLResponse)
async def agent_dashboard_test(request: Request, db: Session = Depends(get_db)):
    """Agent Dashboard - Test (fake data)"""
    
    # Fake user
    fake_user = {"username": "agent1", "role": "agent"}
    
    # Agent info
    agent = {
        'name': 'Alisher Karimov',
        'location': 'Chilonzor tumani, Toshkent'
    }
    
    # KPI
    kpi = {
        'visits_completed': 8,
        'visits_total': 12,
        'visits_percent': 67,
        'today_sales': 1250000,
        'orders': 15,
        'orders_completed': 12,
        'target_achieved': 18500000,
        'target_total': 25000000,
        'target_percent': 74
    }
    
    # Today's Schedule
    schedule = [
        {'customer': 'Anvar Toshmatov', 'time': '09:00', 'address': 'Chilonzor 12-kv', 'completed': True},
        {'customer': 'Dilshod Karimov', 'time': '10:30', 'address': 'Yunusobod 5-kv', 'completed': True},
        {'customer': 'Sardor Usmonov', 'time': '11:45', 'address': 'Mirzo Ulug\'bek 8-kv', 'completed': True},
        {'customer': 'Jasur Rahimov', 'time': '13:00', 'address': 'Yakkasaroy 3-kv', 'completed': False},
        {'customer': 'Bobur Sharipov', 'time': '14:30', 'address': 'Sergeli 7-kv', 'completed': False},
        {'customer': 'Otabek Normatov', 'time': '16:00', 'address': 'Uchtepa 4-kv', 'completed': False}
    ]
    
    # Recent Orders
    recent_orders = [
        {'number': 'ORD-1234', 'customer': 'Anvar Toshmatov', 'total': 450000, 'status_color': 'success', 'status_text': 'Bajarilgan'},
        {'number': 'ORD-1235', 'customer': 'Dilshod Karimov', 'total': 320000, 'status_color': 'warning', 'status_text': 'Jarayonda'},
        {'number': 'ORD-1236', 'customer': 'Sardor Usmonov', 'total': 180000, 'status_color': 'primary', 'status_text': 'Yangi'},
        {'number': 'ORD-1237', 'customer': 'Jasur Rahimov', 'total': 520000, 'status_color': 'success', 'status_text': 'Bajarilgan'},
        {'number': 'ORD-1238', 'customer': 'Bobur Sharipov', 'total': 280000, 'status_color': 'warning', 'status_text': 'Jarayonda'}
    ]
    
    # My Customers
    customers = [
        {'name': 'Anvar Toshmatov', 'phone': '+998 90 123 45 67', 'address': 'Chilonzor 12-kv', 'last_order': 450000},
        {'name': 'Dilshod Karimov', 'phone': '+998 91 234 56 78', 'address': 'Yunusobod 5-kv', 'last_order': 320000},
        {'name': 'Sardor Usmonov', 'phone': '+998 93 345 67 89', 'address': 'Mirzo Ulug\'bek 8-kv', 'last_order': 180000},
        {'name': 'Jasur Rahimov', 'phone': '+998 94 456 78 90', 'address': 'Yakkasaroy 3-kv', 'last_order': 520000},
        {'name': 'Bobur Sharipov', 'phone': '+998 95 567 89 01', 'address': 'Sergeli 7-kv', 'last_order': 280000}
    ]
    
    # Performance (30 days)
    performance = {
        'labels': ['1-kun', '5-kun', '10-kun', '15-kun', '20-kun', '25-kun', '30-kun'],
        'sales': [500000, 1200000, 2100000, 3500000, 5200000, 7100000, 8500000],
        'target': [833333, 1666666, 2500000, 3333333, 4166666, 5000000, 5833333]
    }
    
    return templates.TemplateResponse("dashboards/agent.html", {
        "request": request,
        "page_title": "Agent Dashboard",
        "user": fake_user,
        "agent": agent,
        "kpi": kpi,
        "schedule": schedule,
        "recent_orders": recent_orders,
        "customers": customers,
        "performance": performance
    })



# Production Dashboard - Real Data
@app.get("/dashboard/production", response_class=HTMLResponse)
async def production_dashboard(request: Request, db: Session = Depends(get_db)):
    """Ishlab chiqarish Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Production, Recipe, Product, Employee
    
    # Get user from session cookie
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return RedirectResponse(url="/login", status_code=303)
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Today's production
    today_production = db.query(func.sum(Production.quantity)).filter(
        func.date(Production.date) == today,
        Production.status == 'completed'
    ).scalar() or 0
    
    # Daily plan (placeholder - could be from a Plan table)
    plan = 3000
    efficiency = int((today_production / plan * 100)) if plan > 0 else 0
    
    # Active workers
    active_workers = db.query(func.count(Employee.id)).filter(
        Employee.is_active == True
    ).scalar() or 0
    
    # Raw materials stock percentage (placeholder)
    raw_materials = 72  # Placeholder
    
    metrics = {
        'today_production': int(today_production),
        'plan': plan,
        'active_machines': 0,  # Placeholder - no Machine model
        'total_machines': 0,   # Placeholder
        'efficiency': efficiency,
        'workers': active_workers,
        'shifts': 3,  # Placeholder
        'raw_materials': raw_materials
    }
    
    # Production orders (from Production table)
    production_query = db.query(Production, Recipe, Product).join(
        Recipe, Production.recipe_id == Recipe.id
    ).join(
        Product, Recipe.product_id == Product.id
    ).filter(
        func.date(Production.date) >= today - timedelta(days=1),
        Production.status.in_(['draft', 'completed'])
    ).order_by(Production.date.desc()).limit(10).all()
    
    production_orders = []
    for prod, recipe, product in production_query:
        # Calculate progress based on status
        progress = 100 if prod.status == 'completed' else 50
        deadline = prod.date.strftime('%H:%M') if prod.date else '-'
        
        production_orders.append({
            'product': product.name,
            'quantity': int(prod.quantity),
            'deadline': deadline,
            'progress': progress
        })
    
    if not production_orders:
        production_orders = [{'product': 'Ma\'lumot yo\'q', 'quantity': 0, 'deadline': '-', 'progress': 0}]
    
    # Machines (placeholder - no Machine model)
    machines = [
        {'name': 'Uskunalar ma\'lumoti', 'status': 'unknown', 'operator': '-', 'badge_color': 'secondary', 'status_text': 'Ma\'lumot yo\'q'}
    ]
    
    # Weekly production chart
    chart_labels = []
    chart_data = []
    chart_plan = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        production = db.query(func.sum(Production.quantity)).filter(
            func.date(Production.date) == date,
            Production.status == 'completed'
        ).scalar() or 0
        
        chart_labels.append(['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Juma', 'Shan'][date.weekday()])
        chart_data.append(int(production))
        chart_plan.append(plan)
    
    chart = {
        'labels': chart_labels,
        'data': chart_data,
        'plan': chart_plan
    }
    
    return templates.TemplateResponse("dashboards/production.html", {
        "request": request,
        "page_title": "Ishlab chiqarish Dashboard",
        "user": user,
        "metrics": metrics,
        "production_orders": production_orders,
        "machines": machines,
        "chart": chart
    })


# Production Dashboard - Test (fake data)
@app.get("/test/dashboard/production", response_class=HTMLResponse)
async def production_dashboard_test(request: Request, db: Session = Depends(get_db)):
    """Ishlab chiqarish Dashboard - Test (fake data)"""
    fake_user = {"username": "prod_manager", "role": "production"}
    
    metrics = {
        'today_production': 2500,
        'plan': 3000,
        'active_machines': 8,
        'total_machines': 10,
        'efficiency': 85,
        'workers': 45,
        'shifts': 3,
        'raw_materials': 72
    }
    
    production_orders = [
        {'product': 'Shokolad tort', 'quantity': 500, 'deadline': '16:00', 'progress': 75},
        {'product': 'Medovik', 'quantity': 300, 'deadline': '14:00', 'progress': 100},
        {'product': 'Napoleon', 'quantity': 400, 'deadline': '18:00', 'progress': 45},
        {'product': 'Tiramisu', 'quantity': 200, 'deadline': '15:00', 'progress': 90}
    ]
    
    machines = [
        {'name': 'Mixer #1', 'status': 'active', 'operator': 'Alisher', 'badge_color': 'success', 'status_text': 'Ishlayapti'},
        {'name': 'Mixer #2', 'status': 'active', 'operator': 'Dilshod', 'badge_color': 'success', 'status_text': 'Ishlayapti'},
        {'name': 'Oven #1', 'status': 'active', 'operator': 'Sardor', 'badge_color': 'success', 'status_text': 'Ishlayapti'},
        {'name': 'Oven #2', 'status': 'idle', 'operator': '-', 'badge_color': 'warning', 'status_text': 'Dam olishda'},
        {'name': 'Packaging #1', 'status': 'maintenance', 'operator': 'Texnik', 'badge_color': 'danger', 'status_text': 'Ta\'mirda'}
    ]
    
    chart = {
        'labels': ['Dush', 'Sesh', 'Chor', 'Pay', 'Juma', 'Shan', 'Yak'],
        'data': [2200, 2400, 2600, 2300, 2800, 2500, 2100],
        'plan': [3000, 3000, 3000, 3000, 3000, 2500, 2000]
    }
    
    return templates.TemplateResponse("dashboards/production.html", {
        "request": request,
        "page_title": "Ishlab chiqarish Dashboard",
        "user": fake_user,
        "metrics": metrics,
        "production_orders": production_orders,
        "machines": machines,
        "chart": chart
    })


# Warehouse Dashboard - Real Data
@app.get("/dashboard/warehouse", response_class=HTMLResponse)
async def warehouse_dashboard(request: Request, db: Session = Depends(get_db)):
    """Ombor Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Stock, Product, Category, Purchase, PurchaseItem
    
    # Get user from session cookie
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return RedirectResponse(url="/login", status_code=303)
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Total warehouse value
    total_value = db.query(
        func.sum(Stock.quantity * Product.cost_price)
    ).join(
        Product, Stock.product_id == Product.id
    ).scalar() or 0
    
    # Total products
    total_products = db.query(func.count(Stock.id)).scalar() or 0
    
    # Categories
    categories = db.query(func.count(Category.id)).scalar() or 0
    
    # Today's incoming (purchases)
    today_in = db.query(func.sum(PurchaseItem.quantity)).join(
        Purchase, PurchaseItem.purchase_id == Purchase.id
    ).filter(
        func.date(Purchase.date) == today
    ).scalar() or 0
    
    # Today's outgoing (from orders - we'll use a simple count for now)
    today_out = db.query(func.count(Stock.id)).filter(
        Stock.quantity > 0
    ).scalar() or 0  # Placeholder
    
    metrics = {
        'total_value': float(total_value),
        'total_products': total_products,
        'categories': categories,
        'today_in': int(today_in),
        'today_out': 0  # Placeholder - need stock movement tracking
    }
    
    # Low stock items
    low_stock_items = db.query(Stock, Product).join(
        Product, Stock.product_id == Product.id
    ).filter(
        Stock.quantity < 20
    ).order_by(Stock.quantity).limit(10).all()
    
    low_stock = []
    for stock, product in low_stock_items:
        level = 'critical' if stock.quantity < 10 else 'low'
        badge = 'danger' if stock.quantity < 10 else 'warning'
        low_stock.append({
            'name': product.name,
            'quantity': int(stock.quantity),
            'min_quantity': 20,
            'level': level,
            'badge': badge
        })
    
    if not low_stock:
        low_stock = [{'name': 'Barcha mahsulotlar yetarli', 'quantity': 0, 'min_quantity': 0, 'level': 'ok', 'badge': 'success'}]
    
    # Recent movements (using purchases as proxy)
    recent_purchases = db.query(Purchase, PurchaseItem, Product).join(
        PurchaseItem, Purchase.id == PurchaseItem.purchase_id
    ).join(
        Product, PurchaseItem.product_id == Product.id
    ).filter(
        func.date(Purchase.date) >= week_ago
    ).order_by(Purchase.date.desc()).limit(5).all()
    
    recent_moves = []
    for purchase, item, product in recent_purchases:
        recent_moves.append({
            'product': product.name,
            'quantity': int(item.quantity),
            'type_text': 'Kirim',
            'type_color': 'success',
            'time': purchase.date.strftime('%H:%M')
        })
    
    if not recent_moves:
        recent_moves = [{'product': 'Ma\'lumot yo\'q', 'quantity': 0, 'type_text': '-', 'type_color': 'secondary', 'time': '-'}]
    
    # Weekly movement chart (placeholder with real structure)
    chart_labels = []
    chart_incoming = []
    chart_outgoing = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        incoming = db.query(func.sum(PurchaseItem.quantity)).join(
            Purchase, PurchaseItem.purchase_id == Purchase.id
        ).filter(
            func.date(Purchase.date) == date
        ).scalar() or 0
        
        chart_labels.append(['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Juma', 'Shan'][date.weekday()])
        chart_incoming.append(int(incoming))
        chart_outgoing.append(0)  # Placeholder
    
    chart = {
        'labels': chart_labels,
        'incoming': chart_incoming,
        'outgoing': chart_outgoing
    }
    
    return templates.TemplateResponse("dashboards/warehouse.html", {
        "request": request,
        "page_title": "Ombor Dashboard",
        "user": user,
        "metrics": metrics,
        "low_stock": low_stock,
        "recent_moves": recent_moves,
        "chart": chart
    })


# Warehouse Dashboard - Test (fake data)
@app.get("/test/dashboard/warehouse", response_class=HTMLResponse)
async def warehouse_dashboard_test(request: Request, db: Session = Depends(get_db)):
    """Ombor Dashboard - Test (fake data)"""
    fake_user = {"username": "warehouse_manager", "role": "warehouse"}
    
    metrics = {
        'total_value': 25000000,
        'total_products': 156,
        'categories': 12,
        'today_in': 45,
        'today_out': 38
    }
    
    low_stock = [
        {'name': 'Shokolad', 'quantity': 5, 'min_quantity': 20, 'level': 'critical', 'badge': 'danger'},
        {'name': 'Un', 'quantity': 15, 'min_quantity': 50, 'level': 'low', 'badge': 'warning'},
        {'name': 'Shakar', 'quantity': 25, 'min_quantity': 40, 'level': 'low', 'badge': 'warning'},
        {'name': 'Yog\'', 'quantity': 8, 'min_quantity': 30, 'level': 'critical', 'badge': 'danger'},
        {'name': 'Tuxum', 'quantity': 35, 'min_quantity': 50, 'level': 'low', 'badge': 'warning'}
    ]
    
    recent_moves = [
        {'product': 'Shokolad tort', 'quantity': 50, 'type_text': 'Chiqim', 'type_color': 'danger', 'time': '14:30'},
        {'product': 'Un', 'quantity': 100, 'type_text': 'Kirim', 'type_color': 'success', 'time': '13:15'},
        {'product': 'Medovik', 'quantity': 30, 'type_text': 'Chiqim', 'type_color': 'danger', 'time': '12:45'},
        {'product': 'Shakar', 'quantity': 50, 'type_text': 'Kirim', 'type_color': 'success', 'time': '11:20'},
        {'product': 'Napoleon', 'quantity': 25, 'type_text': 'Chiqim', 'type_color': 'danger', 'time': '10:30'}
    ]
    
    chart = {
        'labels': ['Dush', 'Sesh', 'Chor', 'Pay', 'Juma', 'Shan', 'Yak'],
        'incoming': [120, 150, 180, 140, 200, 160, 130],
        'outgoing': [100, 130, 150, 120, 170, 140, 110]
    }
    
    return templates.TemplateResponse("dashboards/warehouse.html", {
        "request": request,
        "page_title": "Ombor Dashboard",
        "user": fake_user,
        "metrics": metrics,
        "low_stock": low_stock,
        "recent_moves": recent_moves,
        "chart": chart
    })


# Delivery Dashboard - Real Data
@app.get("/dashboard/delivery", response_class=HTMLResponse)
async def delivery_dashboard(request: Request, db: Session = Depends(get_db)):
    """Yetkazib berish Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, case
    from app.models.database import Delivery, Driver, DriverLocation, Order, Partner
    
    # Get user from session cookie
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return RedirectResponse(url="/login", status_code=303)
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Today's deliveries
    total_deliveries = db.query(func.count(Delivery.id)).filter(
        func.date(Delivery.planned_date) == today
    ).scalar() or 0
    
    completed_deliveries = db.query(func.count(Delivery.id)).filter(
        func.date(Delivery.planned_date) == today,
        Delivery.status == 'delivered'
    ).scalar() or 0
    
    percent = int((completed_deliveries / total_deliveries * 100)) if total_deliveries > 0 else 0
    
    # Active drivers
    active_drivers = db.query(func.count(Driver.id)).filter(
        Driver.is_active == True
    ).scalar() or 0
    
    total_drivers = db.query(func.count(Driver.id)).scalar() or 0
    
    # Average delivery time (placeholder - need delivery duration tracking)
    avg_time = 45  # Placeholder
    
    # Delays (deliveries not completed on time)
    delays = db.query(func.count(Delivery.id)).filter(
        func.date(Delivery.planned_date) < today,
        Delivery.status.in_(['pending', 'in_progress'])
    ).scalar() or 0
    
    metrics = {
        'completed': completed_deliveries,
        'total': total_deliveries,
        'percent': percent,
        'active_drivers': active_drivers,
        'total_drivers': total_drivers,
        'avg_time': avg_time,
        'delays': delays
    }
    
    # Today's deliveries with details
    deliveries_query = db.query(Delivery, Driver, Partner).join(
        Driver, Delivery.driver_id == Driver.id
    ).outerjoin(
        Order, Delivery.order_id == Order.id
    ).outerjoin(
        Partner, Order.partner_id == Partner.id
    ).filter(
        func.date(Delivery.planned_date) >= week_ago
    ).order_by(Delivery.planned_date.desc()).limit(20).all()
    
    status_map = {
        'pending': ('Kutilmoqda', 'secondary'),
        'in_progress': ('Yo\'lda', 'warning'),
        'delivered': ('Yetkazilgan', 'success'),
        'failed': ('Bekor qilingan', 'danger')
    }
    
    deliveries = []
    for delivery, driver, partner in deliveries_query:
        status_text, badge_color = status_map.get(delivery.status, ('Noma\'lum', 'secondary'))
        deliveries.append({
            'customer': partner.name if partner else 'Noma\'lum',
            'address': delivery.delivery_address or '-',
            'driver': driver.full_name,
            'status': delivery.status,
            'badge_color': badge_color,
            'status_text': status_text,
            'time': delivery.planned_date.strftime('%H:%M') if delivery.planned_date else '-'
        })
    
    if not deliveries:
        deliveries = [{'customer': 'Ma\'lumot yo\'q', 'address': '-', 'driver': '-', 'status': 'pending', 'badge_color': 'secondary', 'status_text': '-', 'time': '-'}]
    
    # Drivers with their stats
    drivers_query = db.query(
        Driver,
        func.count(Delivery.id).label('delivery_count')
    ).outerjoin(
        Delivery, 
        (Driver.id == Delivery.driver_id) & (func.date(Delivery.planned_date) == today)
    ).group_by(Driver.id).order_by(func.count(Delivery.id).desc()).limit(10).all()
    
    drivers = []
    for driver, delivery_count in drivers_query:
        # Get latest location
        latest_location = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.timestamp.desc()).first()
        
        location_text = 'Noma\'lum'
        if latest_location and latest_location.address:
            location_text = latest_location.address[:30] + '...' if len(latest_location.address) > 30 else latest_location.address
        
        status_color = 'success' if driver.is_active else 'secondary'
        status_text = 'Faol' if driver.is_active else 'Faol emas'
        
        drivers.append({
            'name': driver.full_name,
            'deliveries': delivery_count,
            'location': location_text,
            'status_color': status_color,
            'status_text': status_text
        })
    
    if not drivers:
        drivers = [{'name': 'Ma\'lumot yo\'q', 'deliveries': 0, 'location': '-', 'status_color': 'secondary', 'status_text': '-'}]
    
    # Weekly delivery chart
    chart_labels = []
    chart_completed = []
    chart_delayed = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        
        completed = db.query(func.count(Delivery.id)).filter(
            func.date(Delivery.planned_date) == date,
            Delivery.status == 'delivered'
        ).scalar() or 0
        
        delayed = db.query(func.count(Delivery.id)).filter(
            func.date(Delivery.planned_date) == date,
            Delivery.status.in_(['pending', 'in_progress', 'failed'])
        ).scalar() or 0
        
        chart_labels.append(['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Juma', 'Shan'][date.weekday()])
        chart_completed.append(completed)
        chart_delayed.append(delayed)
    
    chart = {
        'labels': chart_labels,
        'completed': chart_completed,
        'delayed': chart_delayed
    }
    
    return templates.TemplateResponse("dashboards/delivery.html", {
        "request": request,
        "page_title": "Yetkazib berish Dashboard",
        "user": user,
        "metrics": metrics,
        "deliveries": deliveries,
        "drivers": drivers,
        "chart": chart
    })


# Delivery Dashboard - Test (fake data)
@app.get("/test/dashboard/delivery", response_class=HTMLResponse)
async def delivery_dashboard_test(request: Request, db: Session = Depends(get_db)):
    """Yetkazib berish Dashboard - Test (fake data)"""
    fake_user = {"username": "delivery_manager", "role": "delivery"}
    
    metrics = {
        'completed': 28,
        'total': 35,
        'percent': 80,
        'active_drivers': 8,
        'total_drivers': 10,
        'avg_time': 45,
        'delays': 3
    }
    
    deliveries = [
        {'customer': 'Anvar Toshmatov', 'address': 'Chilonzor 12-kv', 'driver': 'Alisher', 'status': 'completed', 'badge_color': 'success', 'status_text': 'Yetkazilgan', 'time': '09:30'},
        {'customer': 'Dilshod Karimov', 'address': 'Yunusobod 5-kv', 'driver': 'Sardor', 'status': 'in-progress', 'badge_color': 'warning', 'status_text': 'Yo\'lda', 'time': '10:15'},
        {'customer': 'Jasur Rahimov', 'address': 'Yakkasaroy 3-kv', 'driver': 'Bobur', 'status': 'in-progress', 'badge_color': 'warning', 'status_text': 'Yo\'lda', 'time': '11:00'},
        {'customer': 'Otabek Normatov', 'address': 'Uchtepa 4-kv', 'driver': 'Jasur', 'status': 'pending', 'badge_color': 'secondary', 'status_text': 'Kutilmoqda', 'time': '13:00'},
        {'customer': 'Sardor Usmonov', 'address': 'Mirzo Ulug\'bek 8-kv', 'driver': 'Dilshod', 'status': 'completed', 'badge_color': 'success', 'status_text': 'Yetkazilgan', 'time': '08:45'}
    ]
    
    drivers = [
        {'name': 'Alisher Karimov', 'deliveries': 5, 'location': 'Chilonzor', 'status_color': 'success', 'status_text': 'Faol'},
        {'name': 'Sardor Usmonov', 'deliveries': 4, 'location': 'Yunusobod', 'status_color': 'success', 'status_text': 'Faol'},
        {'name': 'Bobur Sharipov', 'deliveries': 3, 'location': 'Yakkasaroy', 'status_color': 'success', 'status_text': 'Faol'},
        {'name': 'Jasur Rahimov', 'deliveries': 2, 'location': 'Uchtepa', 'status_color': 'warning', 'status_text': 'Dam olishda'},
        {'name': 'Dilshod Karimov', 'deliveries': 4, 'location': 'Sergeli', 'status_color': 'success', 'status_text': 'Faol'}
    ]
    
    chart = {
        'labels': ['Dush', 'Sesh', 'Chor', 'Pay', 'Juma', 'Shan', 'Yak'],
        'completed': [32, 35, 38, 34, 40, 36, 28],
        'delayed': [3, 2, 4, 3, 5, 2, 3]
    }
    
    return templates.TemplateResponse("dashboards/delivery.html", {
        "request": request,
        "page_title": "Yetkazib berish Dashboard",
        "user": fake_user,
        "metrics": metrics,
        "deliveries": deliveries,
        "drivers": drivers,
        "chart": chart
    })


# ==========================================
# ASOSIY SAHIFALAR
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Bosh sahifa - Dashboard"""
    try:
        # Debug log
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Time: {datetime.now()}\n")
            f.write(f"User: {current_user}\n")
        
        # Agar login qilmagan bo'lsa, login sahifasiga yo'naltirish
        if not current_user:
            with open("debug_home.log", "a", encoding="utf-8") as f:
                f.write("⚠️ User not authenticated, redirecting to login\n")
            return RedirectResponse(url="/login", status_code=303)
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"✅ User authenticated: {current_user.username}\n")
        
        # Statistika
        stats = {
            "tayyor_count": db.query(Product).filter(Product.type == "tayyor").count(),
            "yarim_tayyor_count": db.query(Product).filter(Product.type == "yarim_tayyor").count(),
            "hom_ashyo_count": db.query(Product).filter(Product.type == "hom_ashyo").count(),
            "partners_count": db.query(Partner).count(),
            "employees_count": db.query(Employee).count(),
        }
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"Stats 1: {stats}\n")
        
        # Bugungi savdo
        today = datetime.now().date()
        today_sales = db.query(Order).filter(
            Order.type == "sale",
            Order.date >= today
        ).all()
        stats["today_sales"] = sum(s.total_amount for s in today_sales)
        stats["today_orders"] = len(today_sales)
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"Stats 2: today_sales calculated\n")
        
        # Kassa qoldig'i
        cash = db.query(CashRegister).first()
        stats["cash_balance"] = cash.balance if cash else 0
        
        # Qarzdorlar
        debtors = db.query(Partner).filter(Partner.balance > 0).all()
        stats["total_debt"] = sum(p.balance for p in debtors)
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"✅ Stats calculated, rendering template\n")
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "stats": stats,
            "current_user": current_user,
            "page_title": "Bosh sahifa"
        })
    except Exception as e:
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"❌ HOME PAGE XATO: {str(e)}\n")
            import traceback
            f.write(traceback.format_exc())
        raise


# ==========================================
# MA'LUMOTLAR BO'LIMI
# ==========================================
@app.get("/info", response_class=HTMLResponse)
async def info_index(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Ma'lumotlar bo'limi"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse("info/index.html", {"request": request, "current_user": current_user, "page_title": "Ma'lumotlar"})

# Omborlar bo'limi
@app.get("/info/warehouses", response_class=HTMLResponse)
async def info_warehouses(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Omborlar ro'yxati"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    warehouses = db.query(Warehouse).all()
    return templates.TemplateResponse("info/warehouses.html", {"request": request, "warehouses": warehouses, "current_user": current_user, "page_title": "Omborlar"})

@app.post("/info/warehouses/add")
async def info_warehouses_add(
    request: Request,
    name: str = Form(...),
    address: str = Form(""),
    db: Session = Depends(get_db)
):
    # Dublikat tekshiruvi - nom bo'yicha
    existing_by_name = db.query(Warehouse).filter(Warehouse.name == name).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli ombor allaqachon mavjud!")
    
    warehouse = Warehouse(name=name, code=None, address=address, is_active=True)
    db.add(warehouse)
    db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

@app.post("/info/warehouses/edit/{warehouse_id}")
async def info_warehouses_edit(
    warehouse_id: int,
    name: str = Form(...),
    address: str = Form(""),
    db: Session = Depends(get_db)
):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Ombor topilmadi")
    
    # Dublikat tekshiruvi - nom bo'yicha (o'zidan boshqa)
    existing_by_name = db.query(Warehouse).filter(
        Warehouse.name == name,
        Warehouse.id != warehouse_id
    ).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli ombor allaqachon mavjud!")
    
    warehouse.name = name
    warehouse.address = address
    
    db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

@app.post("/info/warehouses/delete/{warehouse_id}")
async def info_warehouses_delete(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Ombor topilmadi")
    
    db.delete(warehouse)
    db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

# --- WAREHOUSE EXCEL OPERATIONS ---
@app.get("/info/warehouses/export")
async def export_warehouses(db: Session = Depends(get_db)):
    warehouses = db.query(Warehouse).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Warehouses"
    ws.append(["ID", "Kod", "Nomi", "Manzil"])
    for w in warehouses:
        ws.append([w.id, w.code, w.name, w.address])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=omborlar.xlsx"})

@app.get("/info/warehouses/template")
async def template_warehouses():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Manzil"])
    ws.append(["MAIN", "Asosiy ombor", "Toshkent sh."])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=ombor_andoza.xlsx"})

@app.post("/info/warehouses/import")
async def import_warehouses(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, address = row[0], row[1], row[2]
        warehouse = db.query(Warehouse).filter(Warehouse.code == code).first()
        if not warehouse:
            warehouse = Warehouse(code=code, name=name, address=address)
            db.add(warehouse)
        else:
            warehouse.name = name
            warehouse.address = address
        db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

# O'lchov birliklari bo'limi
@app.get("/info/units", response_class=HTMLResponse)
async def info_units(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    units = db.query(Unit).all()
    return templates.TemplateResponse("info/units.html", {"request": request, "units": units, "current_user": current_user, "page_title": "O'lchov birliklari"})

@app.post("/info/units/add")
async def info_units_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(Unit).filter(Unit.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli o'lchov birligi allaqachon mavjud!")
    
    unit = Unit(code=code, name=name)
    db.add(unit)
    db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

@app.post("/info/units/edit/{unit_id}")
async def info_units_edit(
    unit_id: int,
    code: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="O'lchov birligi topilmadi")
    
    existing = db.query(Unit).filter(Unit.code == code, Unit.id != unit_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli o'lchov birligi allaqachon mavjud!")
    
    unit.code = code
    unit.name = name
    db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

@app.post("/info/units/delete/{unit_id}")
async def info_units_delete(unit_id: int, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="O'lchov birligi topilmadi")
    
    db.delete(unit)
    db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

# --- UNITS EXCEL OPERATIONS ---
@app.get("/info/units/export")
async def export_units(db: Session = Depends(get_db)):
    units = db.query(Unit).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Units"
    ws.append(["ID", "Kod", "Nomi"])
    for u in units:
        ws.append([u.id, u.code, u.name])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=olchov_birliklari.xlsx"})

@app.get("/info/units/template")
async def template_units():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi"])
    ws.append(["kg", "Kilogramm"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=birlik_andoza.xlsx"})

@app.post("/info/units/import")
async def import_units(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name = row[0], row[1]
        unit = db.query(Unit).filter(Unit.code == code).first()
        if not unit:
            unit = Unit(code=code, name=name)
            db.add(unit)
        else:
            unit.name = name
        db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

# Kategoriyalar bo'limi
@app.get("/info/categories", response_class=HTMLResponse)
async def info_categories(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    categories = db.query(Category).all()
    return templates.TemplateResponse("info/categories.html", {"request": request, "categories": categories, "current_user": current_user, "page_title": "Kategoriyalar"})

@app.post("/info/categories/add")
async def info_categories_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(Category).filter(Category.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli kategoriya allaqachon mavjud!")
    
    category = Category(code=code, name=name, type=type)
    db.add(category)
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

@app.post("/info/categories/edit/{category_id}")
async def info_categories_edit(
    category_id: int,
    code: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    
    existing = db.query(Category).filter(Category.code == code, Category.id != category_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli kategoriya allaqachon mavjud!")
    
    category.code = code
    category.name = name
    category.type = type
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

@app.post("/info/categories/delete/{category_id}")
async def info_categories_delete(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    
    db.delete(category)
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

# --- CATEGORIES EXCEL OPERATIONS ---
@app.get("/info/categories/export")
async def export_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Categories"
    ws.append(["ID", "Kod", "Nomi", "Turi"])
    for c in categories:
        ws.append([c.id, c.code, c.name, c.type])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kategoriyalar.xlsx"})

@app.get("/info/categories/template")
async def template_categories():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Turi"])
    ws.append(["CAT001", "Shirinliklar", "tayyor"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kategoriya_andoza.xlsx"})

@app.post("/info/categories/import")
async def import_categories(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, type_ = row[0], row[1], row[2]
        category = db.query(Category).filter(Category.code == code).first()
        if not category:
            category = Category(code=code, name=name, type=type_)
            db.add(category)
        else:
            category.name = name
            category.type = type_
        db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

# Kassalar bo'limi
@app.get("/info/cash", response_class=HTMLResponse)
async def info_cash(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    cash_registers = db.query(CashRegister).all()
    return templates.TemplateResponse("info/cash.html", {"request": request, "cash_registers": cash_registers, "current_user": current_user, "page_title": "Kassalar"})

@app.post("/info/cash/add")
async def info_cash_add(
    request: Request,
    name: str = Form(...),
    balance: float = Form(0),
    db: Session = Depends(get_db)
):
    cash = CashRegister(name=name, balance=balance, is_active=True)
    db.add(cash)
    db.commit()
    return RedirectResponse(url="/info/cash", status_code=303)

@app.post("/info/cash/edit/{cash_id}")
async def info_cash_edit(
    cash_id: int,
    name: str = Form(...),
    balance: float = Form(0),
    db: Session = Depends(get_db)
):
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    if not cash:
        raise HTTPException(status_code=404, detail="Kassa topilmadi")
    
    cash.name = name
    cash.balance = balance
    db.commit()
    return RedirectResponse(url="/info/cash", status_code=303)

@app.post("/info/cash/delete/{cash_id}")
async def info_cash_delete(cash_id: int, db: Session = Depends(get_db)):
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    if not cash:
        raise HTTPException(status_code=404, detail="Kassa topilmadi")
    
    db.delete(cash)
    db.commit()
    return RedirectResponse(url="/info/cash", status_code=303)

# Bo'limlar bo'limi
@app.get("/info/departments", response_class=HTMLResponse)
async def info_departments(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    departments = db.query(Department).all()
    return templates.TemplateResponse("info/departments.html", {"request": request, "departments": departments, "current_user": current_user, "page_title": "Bo'limlar"})

@app.post("/info/departments/add")
async def info_departments_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(Department).filter(Department.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli bo'lim allaqachon mavjud!")
    
    department = Department(code=code, name=name, description=description, is_active=True)
    db.add(department)
    db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

@app.post("/info/departments/edit/{department_id}")
async def info_departments_edit(
    department_id: int,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bo'lim topilmadi")
    
    existing = db.query(Department).filter(Department.code == code, Department.id != department_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli bo'lim allaqachon mavjud!")
    
    department.code = code
    department.name = name
    department.description = description
    db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

@app.post("/info/departments/delete/{department_id}")
async def info_departments_delete(department_id: int, db: Session = Depends(get_db)):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bo'lim topilmadi")
    
    db.delete(department)
    db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

# --- DEPARTMENTS EXCEL OPERATIONS ---
@app.get("/info/departments/export")
async def export_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Departments"
    ws.append(["ID", "Kod", "Nomi", "Izoh"])
    for d in departments:
        ws.append([d.id, d.code, d.name, d.description])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=bolimlar.xlsx"})

@app.get("/info/departments/template")
async def template_departments():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Izoh"])
    ws.append(["DEP001", "Ishlab chiqarish", "Asosiy tsex"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=bolim_andoza.xlsx"})

@app.post("/info/departments/import")
async def import_departments(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, description = row[0], row[1], row[2]
        department = db.query(Department).filter(Department.code == code).first()
        if not department:
            department = Department(code=code, name=name, description=description)
            db.add(department)
        else:
            department.name = name
            department.description = description
        db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

# Yo'nalishlar bo'limi
@app.get("/info/directions", response_class=HTMLResponse)
async def info_directions(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    directions = db.query(Direction).all()
    return templates.TemplateResponse("info/directions.html", {"request": request, "directions": directions, "current_user": current_user, "page_title": "Yo'nalishlar"})

@app.post("/info/directions/add")
async def info_directions_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(Direction).filter(Direction.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli yo'nalish allaqachon mavjud!")
    
    direction = Direction(code=code, name=name, description=description, is_active=True)
    db.add(direction)
    db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

@app.post("/info/directions/edit/{direction_id}")
async def info_directions_edit(
    direction_id: int,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    if not direction:
        raise HTTPException(status_code=404, detail="Yo'nalish topilmadi")
    
    existing = db.query(Direction).filter(Direction.code == code, Direction.id != direction_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli yo'nalish allaqachon mavjud!")
    
    direction.code = code
    direction.name = name
    direction.description = description
    db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

@app.post("/info/directions/delete/{direction_id}")
async def info_directions_delete(direction_id: int, db: Session = Depends(get_db)):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    if not direction:
        raise HTTPException(status_code=404, detail="Yo'nalish topilmadi")
    
    db.delete(direction)
    db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

# --- DIRECTIONS EXCEL OPERATIONS ---
@app.get("/info/directions/export")
async def export_directions(db: Session = Depends(get_db)):
    directions = db.query(Direction).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Directions"
    ws.append(["ID", "Kod", "Nomi", "Izoh"])
    for d in directions:
        ws.append([d.id, d.code, d.name, d.description])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=yonalishlar.xlsx"})

@app.get("/info/directions/template")
async def template_directions():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Izoh"])
    ws.append(["DIR001", "Halva", "Halva mahsulotlari"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=yonalish_andoza.xlsx"})

@app.post("/info/directions/import")
async def import_directions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, description = row[0], row[1], row[2]
        direction = db.query(Direction).filter(Direction.code == code).first()
        if not direction:
            direction = Direction(code=code, name=name, description=description)
            db.add(direction)
        else:
            direction.name = name
            direction.description = description
        db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

# Foydalanuvchilar bo'limi
@app.get("/info/users", response_class=HTMLResponse)
async def info_users(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Foydalanuvchilar ro'yxati"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    users = db.query(User).all()
    return templates.TemplateResponse("info/users.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
        "page_title": "Foydalanuvchilar"
    })

@app.post("/info/users/add")
async def info_users_add(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("user"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Yangi foydalanuvchi qo'shish"""
    # Username dublikat tekshiruvi
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{username}' login bilan foydalanuvchi allaqachon mavjud!")
    
    # Yangi foydalanuvchi yaratish
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=is_active
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

@app.post("/info/users/edit/{user_id}")
async def info_users_edit(
    user_id: int,
    username: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("user"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Foydalanuvchini tahrirlash"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Username dublikat tekshiruvi (o'zidan boshqa)
    existing = db.query(User).filter(
        User.username == username,
        User.id != user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{username}' login bilan foydalanuvchi allaqachon mavjud!")
    
    user.username = username
    user.full_name = full_name
    user.role = role
    user.is_active = is_active
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

@app.post("/info/users/change-password/{user_id}")
async def info_users_change_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Foydalanuvchi parolini o'zgartirish"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

@app.post("/info/users/delete/{user_id}")
async def info_users_delete(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Foydalanuvchini o'chirish"""
    # O'zini o'chirishga ruxsat bermaslik
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="O'zingizni o'chira olmaysiz!")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

# --- MAHSULOT DETAIL VA BARCODE ---



@app.get("/products/barcode/{product_id}")
async def product_barcode(product_id: int, download: int = 0, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.barcode:
        return HTMLResponse("<h3>Shtixkod topilmadi</h3>", status_code=404)
    # Barcode rasm faylini yaratish
    barcode_path = f"app/static/images/products/barcode_{product.id}.png"
    if not os.path.exists(barcode_path):
        code128 = barcode.get('code128', product.barcode, writer=ImageWriter())
        code128.save(barcode_path[:-4])
    if download:
        return FileResponse(barcode_path, media_type="image/png", filename=f"barcode_{product.code}.png")
    return FileResponse(barcode_path, media_type="image/png")




# ==========================================
# TOVARLAR
# ==========================================
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import io
import openpyxl

# --- EXPORT PRODUCTS TO EXCEL ---
@app.get("/products/export")
async def export_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products"
    ws.append(["ID", "Kod", "Nomi", "Turi", "Kategoriya", "O'lchov", "Sotish narxi", "Olish narxi"])
    for p in products:
        ws.append([
            p.id, p.code, p.name, p.type,
            p.category.name if p.category else "",
            p.unit.name if p.unit else "",
            p.sale_price, p.purchase_price
        ])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=products.xlsx"})

# --- DOWNLOAD IMPORT TEMPLATE ---
@app.get("/products/template")
async def product_import_template():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Import Template"
    
    # Headers
    headers = ["ID", "Kod", "Nomi", "Turi", "Kategoriya", "O'lchov", "Sotish narxi", "Olish narxi"]
    ws.append(headers)
    
    # Example Row
    example = ["", "P001", "Misol Mahsulot", "tayyor", "Shirinliklar", "dona", 15000, 10000]
    ws.append(example)
    
    # Column width adjustment
    for col in range(1, 9):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
    ws.column_dimensions['C'].width = 30  # Name column
    
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=tovar_andoza.xlsx"})

@app.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return HTMLResponse("<h3>Mahsulot topilmadi</h3>", status_code=404)
    return templates.TemplateResponse("products/detail.html", {"request": request, "product": product})

# --- IMPORT PRODUCTS FROM EXCEL ---
@app.post("/products/import")
async def import_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        code, name, type_, category_name, unit_name, sale_price, purchase_price = row[1:8]
        # Kategoriya va o'lchov birligini topish yoki yaratish
        category = db.query(Category).filter(Category.name == category_name).first()
        if not category and category_name:
            category = Category(name=category_name, code=category_name.lower(), type="product")
            db.add(category)
            db.commit()
        unit = db.query(Unit).filter(Unit.name == unit_name).first()
        if not unit and unit_name:
            unit = Unit(name=unit_name, code=unit_name.lower())
            db.add(unit)
            db.commit()
        # Mahsulotni qo'shish yoki yangilash
        product = db.query(Product).filter(Product.code == code).first()
        if not product:
            product = Product(code=code)
            db.add(product)
        product.name = name
        product.type = type_
        product.category_id = category.id if category else None
        product.unit_id = unit.id if unit else None
        product.sale_price = sale_price or 0
        product.purchase_price = purchase_price or 0
        db.commit()
    return RedirectResponse(url="/products", status_code=303)

@app.get("/products", response_class=HTMLResponse)
async def products_list(request: Request, type: str = "all", db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Tovarlar ro'yxati"""
    query = db.query(Product)
    if type == "tayyor":
        query = query.filter(Product.type == "tayyor")
    elif type == "yarim_tayyor":
        query = query.filter(Product.type == "yarim_tayyor")
    elif type == "hom_ashyo":
        query = query.filter(Product.type == "hom_ashyo")
    
    products = query.all()
    categories = db.query(Category).all()
    units = db.query(Unit).all()
    
    return templates.TemplateResponse("products/list.html", {
        "request": request,
        "products": products,
        "categories": categories,
        "units": units,
        "current_type": type,
        "current_user": current_user,
        "page_title": "Tovarlar"
    })



@app.post("/products/add")
async def product_add(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    category_id: int = Form(None),
    unit_id: int = Form(None),
    barcode: str = Form(None),
    sale_price: float = Form(0),
    purchase_price: float = Form(0),
    db: Session = Depends(get_db)
):
    """Tovar qo'shish"""
    product = Product(
        name=name,
        code=None,
        type=type,
        category_id=category_id if category_id and category_id > 0 else None,
        unit_id=unit_id if unit_id and unit_id > 0 else None,
        barcode=barcode,
        sale_price=sale_price,
        purchase_price=purchase_price,
        image=None
    )
    db.add(product)
    db.commit()
    
    # Kod generatsiya
    product.code = f"P{product.id:05d}"
    db.commit()
    
    return RedirectResponse(url="/products", status_code=303)


@app.post("/products/{product_id}/upload-image")
async def product_upload_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Mahsulot rasmini yuklash"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    
    if image and image.filename:
        import shutil, os
        ext = image.filename.split('.')[-1]
        image_filename = f"{product.code}.{ext}"
        image_path = os.path.join("app/static/images/products", image_filename)
        
        # Papkani yaratish
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        product.image = image_filename
        db.commit()
    
    return RedirectResponse(url="/products", status_code=303)


# ==========================================
# OMBOR
# ==========================================

@app.get("/warehouse", response_class=HTMLResponse)
async def warehouse_list(request: Request, db: Session = Depends(get_db)):
    """Ombor qoldiqlari"""
    warehouses = db.query(Warehouse).all()
    
    # Qoldiqlar
    stocks = db.query(Stock).join(Product).join(Warehouse).all()
    
    return templates.TemplateResponse("warehouse/list.html", {
        "request": request,
        "warehouses": warehouses,
        "stocks": stocks,
        "page_title": "Ombor"
    })


@app.get("/warehouse/movement", response_class=HTMLResponse)
async def warehouse_movement(request: Request, db: Session = Depends(get_db)):
    """Ombor harakatlari"""
    products = db.query(Product).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("warehouse/movement.html", {
        "request": request,
        "products": products,
        "warehouses": warehouses,
        "page_title": "Ombor harakati"
    })


# ==========================================
# TOVAR KIRIMI (PURCHASE)
# ==========================================

@app.get("/purchases", response_class=HTMLResponse)
async def purchases_list(request: Request, db: Session = Depends(get_db)):
    """Tovar kirimlari ro'yxati"""
    purchases = db.query(Purchase).order_by(Purchase.date.desc()).limit(100).all()
    
    return templates.TemplateResponse("purchases/list.html", {
        "request": request,
        "purchases": purchases,
        "page_title": "Tovar kirimlari"
    })


@app.get("/purchases/new", response_class=HTMLResponse)
async def purchase_new(request: Request, db: Session = Depends(get_db)):
    """Yangi tovar kirimi"""
    products = db.query(Product).filter(Product.is_active == True).all()
    partners = db.query(Partner).filter(Partner.type.in_(["supplier", "both"])).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("purchases/new.html", {
        "request": request,
        "products": products,
        "partners": partners,
        "warehouses": warehouses,
        "page_title": "Yangi tovar kirimi"
    })


@app.post("/purchases/create")
async def purchase_create(
    request: Request,
    partner_id: int = Form(...),
    warehouse_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Tovar kirimini yaratish"""
    today = datetime.now()
    count = db.query(Purchase).filter(
        Purchase.date >= today.replace(hour=0, minute=0, second=0)
    ).count()
    number = f"P-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"
    
    purchase = Purchase(
        number=number,
        partner_id=partner_id,
        warehouse_id=warehouse_id,
        status="draft"
    )
    db.add(purchase)
    db.commit()
    
    return RedirectResponse(url=f"/purchases/edit/{purchase.id}", status_code=303)


@app.get("/purchases/edit/{purchase_id}", response_class=HTMLResponse)
async def purchase_edit(request: Request, purchase_id: int, db: Session = Depends(get_db)):
    """Tovar kirimini tahrirlash"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    products = db.query(Product).filter(Product.is_active == True).all()
    
    return templates.TemplateResponse("purchases/edit.html", {
        "request": request,
        "purchase": purchase,
        "products": products,
        "page_title": f"Tovar kirimi: {purchase.number}"
    })


@app.post("/purchases/{purchase_id}/add-item")
async def purchase_add_item(
    purchase_id: int,
    product_id: int = Form(...),
    quantity: float = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db)
):
    """Tovar kirimiga mahsulot qo'shish"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    total = quantity * price
    item = PurchaseItem(
        purchase_id=purchase_id,
        product_id=product_id,
        quantity=quantity,
        price=price,
        total=total
    )
    db.add(item)
    
    purchase.total = db.query(PurchaseItem).filter(
        PurchaseItem.purchase_id == purchase_id
    ).with_entities(db.func.sum(PurchaseItem.total)).scalar() or 0
    purchase.total += total
    
    db.commit()
    return RedirectResponse(url=f"/purchases/edit/{purchase_id}", status_code=303)


@app.post("/purchases/{purchase_id}/confirm")
async def purchase_confirm(purchase_id: int, db: Session = Depends(get_db)):
    """Tovar kirimini tasdiqlash va ombor qoldiqlarini yangilash"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    if purchase.status != "draft":
        raise HTTPException(status_code=400, detail="Faqat qoralama holatidagi kirimlarni tasdiqlash mumkin")
    
    for item in purchase.items:
        stock = db.query(Stock).filter(
            Stock.warehouse_id == purchase.warehouse_id,
            Stock.product_id == item.product_id
        ).first()
        
        if stock:
            stock.quantity += item.quantity
        else:
            stock = Stock(
                warehouse_id=purchase.warehouse_id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.add(stock)
        
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.purchase_price = item.price
    
    purchase.status = "confirmed"
    
    if purchase.partner_id:
        partner = db.query(Partner).filter(Partner.id == purchase.partner_id).first()
        if partner:
            partner.balance -= purchase.total
    
    db.commit()
    return RedirectResponse(url=f"/purchases", status_code=303)


# ==========================================
# MIJOZLAR
# ==========================================

@app.get("/partners", response_class=HTMLResponse)
async def partners_list(request: Request, type: str = "all", db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Kontragentlar ro'yxati"""
    query = db.query(Partner)
    if type != "all":
        query = query.filter(Partner.type == type)
    
    partners = query.all()
    
    return templates.TemplateResponse("partners/list.html", {
        "request": request,
        "partners": partners,
        "current_type": type,
        "current_user": current_user,
        "page_title": "Kontragentlar"
    })


@app.post("/partners/add")
async def partner_add(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    credit_limit: float = Form(0),
    discount_percent: float = Form(0),
    db: Session = Depends(get_db)
):
    """Kontragent qo'shish"""
    # Dublikat tekshiruvi - nom bo'yicha
    existing_by_name = db.query(Partner).filter(Partner.name == name).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli kontragent allaqachon mavjud!")
    
    # Dublikat tekshiruvi - telefon bo'yicha (agar telefon kiritilgan bo'lsa)
    if phone and phone.strip():
        existing_by_phone = db.query(Partner).filter(Partner.phone == phone).first()
        if existing_by_phone:
            raise HTTPException(status_code=400, detail=f"'{phone}' telefon raqamli kontragent allaqachon mavjud!")
    
    partner = Partner(
        name=name,
        code=None,  # Kod kerak emas
        type=type,
        phone=phone,
        address=address,
        credit_limit=credit_limit,
        discount_percent=discount_percent
    )
    db.add(partner)
    db.commit()
    return RedirectResponse(url="/partners", status_code=303)


@app.post("/partners/edit/{partner_id}")
async def partner_edit(
    partner_id: int,
    name: str = Form(...),
    type: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    credit_limit: float = Form(0),
    discount_percent: float = Form(0),
    db: Session = Depends(get_db)
):
    """Kontragentni tahrirlash"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Kontragent topilmadi")
    
    # Dublikat tekshiruvi - nom bo'yicha (o'zidan boshqa)
    existing_by_name = db.query(Partner).filter(
        Partner.name == name,
        Partner.id != partner_id
    ).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli kontragent allaqachon mavjud!")
    
    # Dublikat tekshiruvi - telefon bo'yicha (agar telefon kiritilgan bo'lsa va o'zidan boshqa)
    if phone and phone.strip():
        existing_by_phone = db.query(Partner).filter(
            Partner.phone == phone,
            Partner.id != partner_id
        ).first()
        if existing_by_phone:
            raise HTTPException(status_code=400, detail=f"'{phone}' telefon raqamli kontragent allaqachon mavjud!")
    
    partner.name = name
    # partner.code o'zgartirilmaydi - avtomatik generatsiya qilingan
    partner.type = type
    partner.phone = phone
    partner.address = address
    partner.credit_limit = credit_limit
    partner.discount_percent = discount_percent
    
    db.commit()
    return RedirectResponse(url="/partners", status_code=303)


@app.post("/partners/delete/{partner_id}")
async def partner_delete(partner_id: int, db: Session = Depends(get_db)):
    """Kontragentni o'chirish"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Kontragent topilmadi")
    
    # Kontragent bilan bog'liq buyurtmalar borligini tekshirish
    has_orders = db.query(Order).filter(Order.partner_id == partner_id).first()
    has_purchases = db.query(Purchase).filter(Purchase.partner_id == partner_id).first()
    
    if has_orders or has_purchases:
        raise HTTPException(
            status_code=400, 
            detail="Bu kontragent bilan bog'liq buyurtmalar yoki kirimlar mavjud. O'chirish mumkin emas."
        )
    
    db.delete(partner)
    db.commit()
    return RedirectResponse(url="/partners", status_code=303)


# --- PARTNERS EXCEL OPERATIONS ---
@app.get("/partners/export")
async def export_partners(db: Session = Depends(get_db)):
    partners = db.query(Partner).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Partners"
    ws.append(["ID", "Kod", "Nomi", "Turi", "Telefon", "Manzil", "Kredit Limit", "Chegirma %"])
    for p in partners:
        ws.append([p.id, p.code, p.name, p.type, p.phone, p.address, p.credit_limit, p.discount_percent])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kontragentlar.xlsx"})

@app.get("/partners/template")
async def template_partners():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Nomi", "Turi", "Telefon", "Manzil", "Kredit Limit", "Chegirma %"])
    ws.append(["Mijoz MCHJ", "customer", "+998901234567", "Toshkent", 1000000, 0])
    ws.append(["Yetkazib Beruvchi", "supplier", "+998909876543", "Samarqand", 0, 0])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kontragent_andoza.xlsx"})

@app.post("/partners/import")
async def import_partners(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        name, type_, phone, address, credit_limit, discount_percent = row[0:6]
        partner = db.query(Partner).filter(Partner.name == name).first()
        if not partner:
            # Kod generatsiya
            count = db.query(Partner).count()
            code = f"P{count + 1:04d}"
            partner = Partner(
                code=code,
                name=name, 
                type=type_, 
                phone=phone, 
                address=address, 
                credit_limit=credit_limit, 
                discount_percent=discount_percent
            )
            db.add(partner)
        else:
            partner.phone = phone
            partner.address = address
            partner.credit_limit = credit_limit
            partner.discount_percent = discount_percent
        db.commit()
    return RedirectResponse(url="/partners", status_code=303)


# ==========================================
# SAVDO
# ==========================================

@app.get("/sales", response_class=HTMLResponse)
async def sales_list(request: Request, db: Session = Depends(get_db)):
    """Sotuvlar ro'yxati"""
    orders = db.query(Order).filter(Order.type == "sale").order_by(Order.date.desc()).limit(100).all()
    
    return templates.TemplateResponse("sales/list.html", {
        "request": request,
        "orders": orders,
        "page_title": "Sotuvlar"
    })


@app.get("/sales/new", response_class=HTMLResponse)
async def sales_new(request: Request, db: Session = Depends(get_db)):
    """Yangi sotuv"""
    products = db.query(Product).filter(Product.type.in_(["tayyor", "yarim_tayyor"]), Product.is_active == True).all()
    partners = db.query(Partner).filter(Partner.type.in_(["customer", "both"])).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("sales/new.html", {
        "request": request,
        "products": products,
        "partners": partners,
        "warehouses": warehouses,
        "page_title": "Yangi sotuv"
    })


@app.post("/sales/create")
async def sales_create(
    request: Request,
    partner_id: int = Form(...),
    warehouse_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Sotuv yaratish"""
    # Yangi raqam generatsiya
    last_order = db.query(Order).filter(Order.type == "sale").order_by(Order.id.desc()).first()
    new_number = f"S-{datetime.now().strftime('%Y%m%d')}-{(last_order.id + 1) if last_order else 1:04d}"
    
    order = Order(
        number=new_number,
        type="sale",
        partner_id=partner_id,
        warehouse_id=warehouse_id,
        status="draft"
    )
    db.add(order)
    db.commit()
    
    return RedirectResponse(url=f"/sales/edit/{order.id}", status_code=303)


# ==========================================
# MOLIYA
# ==========================================

@app.get("/finance", response_class=HTMLResponse)
async def finance(request: Request, db: Session = Depends(get_db)):
    """Moliya - kassa"""
    cash_registers = db.query(CashRegister).all()
    
    # So'nggi to'lovlar
    payments = db.query(Payment).order_by(Payment.date.desc()).limit(50).all()
    
    # Bugungi statistika
    today = datetime.now().date()
    today_income = db.query(Payment).filter(
        Payment.type == "income",
        Payment.date >= today
    ).all()
    today_expense = db.query(Payment).filter(
        Payment.type == "expense",
        Payment.date >= today
    ).all()
    
    stats = {
        "today_income": sum(p.amount for p in today_income),
        "today_expense": sum(p.amount for p in today_expense),
    }
    
    return templates.TemplateResponse("finance/index.html", {
        "request": request,
        "cash_registers": cash_registers,
        "payments": payments,
        "stats": stats,
        "page_title": "Moliya"
    })


# ==========================================
# XODIMLAR
# ==========================================

@app.get("/employees", response_class=HTMLResponse)
async def employees_list(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Xodimlar ro'yxati"""
    employees = db.query(Employee).all()
    
    return templates.TemplateResponse("employees/list.html", {
        "request": request,
        "employees": employees,
        "current_user": current_user,
        "page_title": "Xodimlar"
    })


@app.post("/employees/add")
async def employee_add(
    request: Request,
    full_name: str = Form(...),
    code: str = Form(...),
    position: str = Form(""),
    department: str = Form(""),
    phone: str = Form(""),
    salary: float = Form(0),
    db: Session = Depends(get_db)
):
    """Xodim qo'shish"""
    employee = Employee(
        full_name=full_name,
        code=code,
        position=position,
        department=department,
        phone=phone,
        salary=salary
    )
    db.add(employee)
    db.commit()
    return RedirectResponse(url="/employees", status_code=303)


# --- EMPLOYEES EXCEL OPERATIONS ---
@app.get("/employees/export")
async def export_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(["ID", "Kod", "F.I.SH", "Lavozim", "Bo'lim", "Telefon", "Oylik"])
    for e in employees:
        ws.append([e.id, e.code, e.full_name, e.position, e.department, e.phone, e.salary])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=xodimlar.xlsx"})

@app.get("/employees/template")
async def template_employees():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "F.I.SH", "Lavozim", "Bo'lim", "Telefon", "Oylik"])
    ws.append(["X001", "Aliyev Vali", "Ishchi", "Ishlab chiqarish", "+998901234567", 3000000])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=xodim_andoza.xlsx"})

@app.post("/employees/import")
async def import_employees(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, full_name, position, department, phone, salary = row[0:6]
        employee = db.query(Employee).filter(Employee.code == code).first()
        if not employee:
            employee = Employee(
                code=code, 
                full_name=full_name, 
                position=position, 
                department=department, 
                phone=phone, 
                salary=salary
            )
            db.add(employee)
        else:
            employee.full_name = full_name
            employee.position = position
            employee.department = department
            employee.phone = phone
            employee.salary = salary
        db.commit()
    return RedirectResponse(url="/employees", status_code=303)


# ==========================================
# HISOBOTLAR
# ==========================================

@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    """Hisobotlar"""
    return templates.TemplateResponse("reports/index.html", {
        "request": request,
        "page_title": "Hisobotlar"
    })


@app.get("/reports/sales", response_class=HTMLResponse)
async def report_sales(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    """Savdo hisoboti"""
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    orders = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= start_date,
        Order.date <= end_date + " 23:59:59"
    ).all()
    
    total = sum(o.total for o in orders)
    
    return templates.TemplateResponse("reports/sales.html", {
        "request": request,
        "orders": orders,
        "total": total,
        "start_date": start_date,
        "end_date": end_date,
        "page_title": "Savdo hisoboti"
    })


@app.get("/reports/stock", response_class=HTMLResponse)
async def report_stock(request: Request, db: Session = Depends(get_db)):
    """Qoldiq hisoboti"""
    stocks = db.query(Stock).join(Product).all()
    
    return templates.TemplateResponse("reports/stock.html", {
        "request": request,
        "stocks": stocks,
        "page_title": "Qoldiq hisoboti"
    })


@app.get("/reports/debts", response_class=HTMLResponse)
async def report_debts(request: Request, db: Session = Depends(get_db)):
    """Qarzdorlik hisoboti"""
    debtors = db.query(Partner).filter(Partner.balance != 0).all()
    
    total_debt = sum(p.balance for p in debtors if p.balance > 0)
    total_credit = sum(abs(p.balance) for p in debtors if p.balance < 0)
    
    return templates.TemplateResponse("reports/debts.html", {
        "request": request,
        "debtors": debtors,
        "total_debt": total_debt,
        "total_credit": total_credit,
        "page_title": "Qarzdorlik hisoboti"
    })


# ==========================================
# ISHLAB CHIQARISH
# ==========================================

@app.get("/production", response_class=HTMLResponse)
async def production_dashboard(request: Request, db: Session = Depends(get_db)):
    """Ishlab chiqarish bosh sahifasi"""
    today = datetime.now().date()
    
    # Statistika
    total_recipes = db.query(Recipe).filter(Recipe.is_active == True).count()
    today_productions = db.query(Production).filter(
        Production.date >= today,
        Production.status == "completed"
    ).all()
    today_quantity = sum(p.quantity for p in today_productions)
    
    pending_productions = db.query(Production).filter(
        Production.status == "draft"
    ).count()
    
    # Oxirgi ishlab chiqarishlar
    recent_productions = db.query(Production).order_by(
        Production.date.desc()
    ).limit(10).all()
    
    # Retseptlar
    recipes = db.query(Recipe).filter(Recipe.is_active == True).all()
    
    return templates.TemplateResponse("production/index.html", {
        "request": request,
        "total_recipes": total_recipes,
        "today_quantity": today_quantity,
        "pending_productions": pending_productions,
        "recent_productions": recent_productions,
        "recipes": recipes,
        "page_title": "Ishlab chiqarish"
    })


@app.get("/production/recipes", response_class=HTMLResponse)
async def production_recipes(request: Request, db: Session = Depends(get_db)):
    """Retseptlar ro'yxati"""
    recipes = db.query(Recipe).all()
    products = db.query(Product).filter(Product.type.in_(["tayyor", "yarim_tayyor"])).all()
    materials = db.query(Product).filter(Product.type == "hom_ashyo").all()
    
    return templates.TemplateResponse("production/recipes.html", {
        "request": request,
        "recipes": recipes,
        "products": products,
        "materials": materials,
        "page_title": "Retseptlar"
    })


@app.get("/production/recipes/{recipe_id}", response_class=HTMLResponse)
async def production_recipe_detail(request: Request, recipe_id: int, db: Session = Depends(get_db)):
    """Retsept tafsilotlari"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Retsept topilmadi")
    
    materials = db.query(Product).filter(Product.type.in_(["hom_ashyo", "yarim_tayyor", "tayyor"])).all()
    
    return templates.TemplateResponse("production/recipe_detail.html", {
        "request": request,
        "recipe": recipe,
        "materials": materials,
        "page_title": f"Retsept: {recipe.name}"
    })


@app.post("/production/recipes/add")
async def add_recipe(
    request: Request,
    name: str = Form(...),
    product_id: int = Form(...),
    output_quantity: float = Form(1),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Yangi retsept qo'shish"""
    recipe = Recipe(
        name=name,
        product_id=product_id,
        output_quantity=output_quantity,
        description=description,
        is_active=True
    )
    db.add(recipe)
    db.commit()
    return RedirectResponse(url=f"/production/recipes/{recipe.id}", status_code=303)


@app.post("/production/recipes/{recipe_id}/add-item")
async def add_recipe_item(
    recipe_id: int,
    product_id: int = Form(...),
    quantity: float = Form(...),
    db: Session = Depends(get_db)
):
    """Retseptga xom ashyo qo'shish"""
    item = RecipeItem(
        recipe_id=recipe_id,
        product_id=product_id,
        quantity=quantity
    )
    db.add(item)
    db.commit()
    return RedirectResponse(url=f"/production/recipes/{recipe_id}", status_code=303)


@app.get("/production/orders", response_class=HTMLResponse)
async def production_orders(request: Request, db: Session = Depends(get_db)):
    """Ishlab chiqarish buyurtmalari"""
    productions = db.query(Production).order_by(Production.date.desc()).all()
    
    return templates.TemplateResponse("production/orders.html", {
        "request": request,
        "productions": productions,
        "page_title": "Ishlab chiqarish buyurtmalari"
    })


@app.get("/production/new", response_class=HTMLResponse)
async def production_new(request: Request, db: Session = Depends(get_db)):
    """Yangi ishlab chiqarish"""
    recipes = db.query(Recipe).filter(Recipe.is_active == True).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("production/new_order.html", {
        "request": request,
        "recipes": recipes,
        "warehouses": warehouses,
        "page_title": "Yangi ishlab chiqarish"
    })



from typing import List

@app.post("/production/create")
async def create_production(
    request: Request,
    recipe_id: int = Form(...),
    warehouse_id: int = Form(...),
    quantity: float = Form(...),
    note: str = Form(""),
    material_product_id: List[int] = Form([]),
    material_quantity: List[float] = Form([]),
    db: Session = Depends(get_db)
):
    """Ishlab chiqarish yaratish (tarkibni qo'lda o'zgartirish bilan)"""
    today = datetime.now()
    count = db.query(Production).filter(
        Production.date >= today.replace(hour=0, minute=0, second=0)
    ).count()
    number = f"PR-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(3)}"

    production = Production(
        number=number,
        recipe_id=recipe_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        note=note,
        status="draft"
    )
    db.add(production)
    db.flush()  # production.id olish uchun

    # Foydalanuvchi o'zgartirgan tarkibni saqlash (Production tarkibi sifatida)
    # (Agar kerak bo'lsa, alohida ProductionMaterial model qilish mumkin, hozircha RecipeItem orqali)
    for pid, qty in zip(material_product_id, material_quantity):
        if pid and qty:
            db.add(RecipeItem(recipe_id=production.id, product_id=pid, quantity=qty))

    db.commit()
    return RedirectResponse(url="/production/orders", status_code=303)


@app.post("/production/{prod_id}/complete")
async def complete_production(prod_id: int, db: Session = Depends(get_db)):
    """Ishlab chiqarishni yakunlash"""
    production = db.query(Production).filter(Production.id == prod_id).first()
    if not production:
        raise HTTPException(status_code=404, detail="Topilmadi")
    
    recipe = db.query(Recipe).filter(Recipe.id == production.recipe_id).first()
    
    # Xom ashyolarni ayirish
    for item in recipe.items:
        stock = db.query(Stock).filter(
            Stock.warehouse_id == production.warehouse_id,
            Stock.product_id == item.product_id
        ).first()
        if stock:
            stock.quantity -= item.quantity * production.quantity
    
    # Tayyor mahsulotni qo'shish
    product_stock = db.query(Stock).filter(
        Stock.warehouse_id == production.warehouse_id,
        Stock.product_id == recipe.product_id
    ).first()
    
    if product_stock:
        product_stock.quantity += production.quantity * recipe.output_quantity
    else:
        new_stock = Stock(
            warehouse_id=production.warehouse_id,
            product_id=recipe.product_id,
            quantity=production.quantity * recipe.output_quantity
        )
        db.add(new_stock)
    
    production.status = "completed"
    db.commit()
    return RedirectResponse(url="/production/orders", status_code=303)


@app.post("/production/{prod_id}/cancel")
async def cancel_production(prod_id: int, db: Session = Depends(get_db)):
    """Ishlab chiqarishni bekor qilish"""
    production = db.query(Production).filter(Production.id == prod_id).first()
    if not production:
        raise HTTPException(status_code=404, detail="Topilmadi")
    
    production.status = "cancelled"
    db.commit()
    return RedirectResponse(url="/production/orders", status_code=303)


# ==========================================
# API (Telegram bot uchun)
# ==========================================

@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    """Statistika API"""
    today = datetime.now().date()
    
    today_sales = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= today
    ).all()
    
    cash = db.query(CashRegister).first()
    
    return {
        "today_sales": sum(o.total for o in today_sales),
        "today_orders": len(today_sales),
        "cash_balance": cash.balance if cash else 0,
        "products_count": db.query(Product).count(),
        "partners_count": db.query(Partner).count(),
    }


@app.get("/api/products")
async def api_products(db: Session = Depends(get_db)):
    """Tovarlar API"""
    products = db.query(Product).filter(Product.is_active == True).all()
    return [{"id": p.id, "name": p.name, "code": p.code, "price": p.sale_price} for p in products]


@app.get("/api/partners")
async def api_partners(db: Session = Depends(get_db)):
    """Kontragentlar API"""
    partners = db.query(Partner).filter(Partner.is_active == True).all()
    return [{"id": p.id, "name": p.name, "balance": p.balance} for p in partners]


# ==========================================
# AGENTLAR
# ==========================================

@app.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request, db: Session = Depends(get_db)):
    """Agentlar ro'yxati"""
    agents = db.query(Agent).all()
    
    # Har bir agent uchun oxirgi lokatsiya
    for agent in agents:
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        agent.last_location = last_loc
        
        # Bugungi tashriflar
        today = datetime.now().date()
        agent.today_visits = db.query(Visit).filter(
            Visit.agent_id == agent.id,
            Visit.visit_date >= today
        ).count()
    
    return templates.TemplateResponse("agents/list.html", {
        "request": request,
        "agents": agents,
        "page_title": "Agentlar"
    })


@app.post("/agents/add")
async def agent_add(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(""),
    region: str = Form(""),
    telegram_id: str = Form(""),
    db: Session = Depends(get_db)
):
    """Agent qo'shish"""
    agent = Agent(
        full_name=full_name,
        phone=phone,
        region=region,
        telegram_id=telegram_id
    )
    db.add(agent)
    db.commit()
    return RedirectResponse(url="/agents", status_code=303)


@app.get("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_detail(request: Request, agent_id: int, db: Session = Depends(get_db)):
    """Agent tafsilotlari"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent topilmadi")
    
    # Oxirgi lokatsiyalar
    locations = db.query(AgentLocation).filter(
        AgentLocation.agent_id == agent_id
    ).order_by(AgentLocation.recorded_at.desc()).limit(50).all()
    
    # Tashriflar
    visits = db.query(Visit).filter(
        Visit.agent_id == agent_id
    ).order_by(Visit.visit_date.desc()).limit(30).all()
    
    return templates.TemplateResponse("agents/detail.html", {
        "request": request,
        "agent": agent,
        "locations": locations,
        "visits": visits,
        "page_title": f"Agent: {agent.full_name}"
    })


# ==========================================
# YETKAZIB BERISH
# ==========================================

@app.get("/delivery", response_class=HTMLResponse)
async def delivery_list(request: Request, db: Session = Depends(get_db)):
    """Yetkazib berish ro'yxati"""
    drivers = db.query(Driver).all()
    
    # Har bir haydovchi uchun statistika
    for driver in drivers:
        last_loc = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.recorded_at.desc()).first()
        driver.last_location = last_loc
        
        # Bugungi yetkazilganlar
        today = datetime.now().date()
        driver.today_deliveries = db.query(Delivery).filter(
            Delivery.driver_id == driver.id,
            Delivery.created_at >= today
        ).count()
        
        driver.pending_deliveries = db.query(Delivery).filter(
            Delivery.driver_id == driver.id,
            Delivery.status == "pending"
        ).count()
    
    # Barcha yetkazishlar
    deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).limit(50).all()
    
    return templates.TemplateResponse("delivery/list.html", {
        "request": request,
        "drivers": drivers,
        "deliveries": deliveries,
        "page_title": "Yetkazib berish"
    })


@app.post("/drivers/add")
async def driver_add(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(""),
    vehicle_number: str = Form(""),
    vehicle_type: str = Form(""),
    telegram_id: str = Form(""),
    db: Session = Depends(get_db)
):
    """Haydovchi qo'shish"""
    driver = Driver(
        full_name=full_name,
        phone=phone,
        vehicle_number=vehicle_number,
        vehicle_type=vehicle_type,
        telegram_id=telegram_id
    )
    db.add(driver)
    db.commit()
    return RedirectResponse(url="/delivery", status_code=303)


@app.get("/delivery/{driver_id}", response_class=HTMLResponse)
async def driver_detail(request: Request, driver_id: int, db: Session = Depends(get_db)):
    """Haydovchi tafsilotlari"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    
    # Lokatsiya tarixi
    locations = db.query(DriverLocation).filter(
        DriverLocation.driver_id == driver_id
    ).order_by(DriverLocation.recorded_at.desc()).limit(100).all()
    
    # Yetkazishlar
    deliveries = db.query(Delivery).filter(
        Delivery.driver_id == driver_id
    ).order_by(Delivery.created_at.desc()).limit(30).all()
    
    return templates.TemplateResponse("delivery/detail.html", {
        "request": request,
        "driver": driver,
        "locations": locations,
        "deliveries": deliveries,
        "page_title": f"Haydovchi: {driver.full_name}"
    })


# ==========================================
# XARITA
# ==========================================

@app.get("/map", response_class=HTMLResponse)
async def map_view(request: Request, db: Session = Depends(get_db)):
    """Xarita - barcha joylashuvlar"""
    
    # Agentlar
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    agent_markers = []
    for agent in agents:
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        if last_loc:
            agent_markers.append({
                "id": agent.id,
                "name": agent.full_name,
                "type": "agent",
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.strftime("%H:%M")
            })
    
    # Haydovchilar
    drivers = db.query(Driver).filter(Driver.is_active == True).all()
    driver_markers = []
    for driver in drivers:
        last_loc = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.recorded_at.desc()).first()
        if last_loc:
            driver_markers.append({
                "id": driver.id,
                "name": driver.full_name,
                "type": "driver",
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.strftime("%H:%M"),
                "vehicle": driver.vehicle_number
            })
    
    # Mijozlar
    partners = db.query(Partner).filter(Partner.is_active == True).all()
    partner_locations = db.query(PartnerLocation).all()
    partner_markers = []
    for loc in partner_locations:
        partner = db.query(Partner).filter(Partner.id == loc.partner_id).first()
        if partner and loc.latitude and loc.longitude:
            partner_markers.append({
                "id": loc.partner_id,
                "name": partner.name,
                "type": "partner",
                "lat": loc.latitude,
                "lng": loc.longitude,
                "address": loc.address
            })
    
    return templates.TemplateResponse("map/index.html", {
        "request": request,
        "agents": agents,
        "drivers": drivers,
        "partner_locations": partner_locations,
        "agent_markers": agent_markers,
        "driver_markers": driver_markers,
        "partner_markers": partner_markers,
        "page_title": "Xarita"
    })


# ==========================================
# SUPERVAYZER DASHBOARD
# ==========================================

@app.get("/supervisor", response_class=HTMLResponse)
async def supervisor_dashboard(request: Request, db: Session = Depends(get_db)):
    """Supervayzer dashboard"""
    today = datetime.now().date()
    
    # Agentlar statistikasi
    total_agents = db.query(Agent).filter(Agent.is_active == True).count()
    active_agents = 0
    for agent in db.query(Agent).filter(Agent.is_active == True).all():
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id,
            AgentLocation.recorded_at >= today
        ).first()
        if last_loc:
            active_agents += 1
    
    # Bugungi tashriflar
    today_visits = db.query(Visit).filter(Visit.visit_date >= today).count()
    
    # Bugungi buyurtmalar
    today_orders = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= today
    ).all()
    today_sales_sum = sum(o.total for o in today_orders)
    
    # Yetkazib berish statistikasi
    total_drivers = db.query(Driver).filter(Driver.is_active == True).count()
    pending_deliveries = db.query(Delivery).filter(Delivery.status == "pending").count()
    today_delivered = db.query(Delivery).filter(
        Delivery.status == "delivered",
        Delivery.delivered_at >= today
    ).count()
    
    # Agent reytingi (bugungi savdo bo'yicha)
    agent_stats = []
    for agent in db.query(Agent).filter(Agent.is_active == True).all():
        visits = db.query(Visit).filter(
            Visit.agent_id == agent.id,
            Visit.visit_date >= today
        ).count()
        
        # So'nggi lokatsiya
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        
        agent_stats.append({
            "agent": agent,
            "visits": visits,
            "last_seen": last_loc.recorded_at if last_loc else None,
            "is_online": last_loc and (datetime.now() - last_loc.recorded_at).seconds < 600 if last_loc else False
        })
    
    # Eng faol agentlar
    agent_stats.sort(key=lambda x: x["visits"], reverse=True)
    
    stats = {
        "total_agents": total_agents,
        "active_agents": active_agents,
        "today_visits": today_visits,
        "today_orders": len(today_orders),
        "today_sales": today_sales_sum,
        "total_drivers": total_drivers,
        "pending_deliveries": pending_deliveries,
        "today_delivered": today_delivered,
    }
    
    # Barcha agentlar va haydovchilar
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    drivers = db.query(Driver).filter(Driver.is_active == True).all()
    
    # Oxirgi tashriflar va yetkazishlar
    recent_visits = db.query(Visit).order_by(Visit.visit_date.desc()).limit(10).all()
    recent_deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse("supervisor/dashboard.html", {
        "request": request,
        "stats": stats,
        "agents": agents,
        "drivers": drivers,
        "agent_stats": agent_stats[:10],
        "recent_visits": recent_visits,
        "recent_deliveries": recent_deliveries,
        "page_title": "Supervayzer",
        "now": datetime.now()
    })


# ==========================================
# POST Routes - Agent va Driver qo'shish
# ==========================================

@app.post("/agents/add")
async def add_agent(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(None),
    region: str = Form(None),
    telegram_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """Yangi agent qo'shish"""
    # Kod generatsiya
    last_agent = db.query(Agent).order_by(Agent.id.desc()).first()
    code = f"AG{str((last_agent.id if last_agent else 0) + 1).zfill(3)}"
    
    agent = Agent(
        code=code,
        full_name=full_name,
        phone=phone,
        region=region,
        telegram_id=telegram_id,
        is_active=True
    )
    db.add(agent)
    db.commit()
    return RedirectResponse(url="/agents", status_code=303)


@app.post("/delivery/add-driver")
async def add_driver(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(None),
    vehicle_type: str = Form(None),
    vehicle_number: str = Form(None),
    telegram_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """Yangi haydovchi qo'shish"""
    # Kod generatsiya
    last_driver = db.query(Driver).order_by(Driver.id.desc()).first()
    code = f"DR{str((last_driver.id if last_driver else 0) + 1).zfill(3)}"
    
    driver = Driver(
        code=code,
        full_name=full_name,
        phone=phone,
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number,
        telegram_id=telegram_id,
        is_active=True
    )
    db.add(driver)
    db.commit()
    return RedirectResponse(url="/delivery", status_code=303)


@app.post("/delivery/add-order")
async def add_delivery_order(
    request: Request,
    driver_id: int = Form(...),
    order_number: str = Form(...),
    delivery_address: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Yangi yetkazish buyurtmasi qo'shish"""
    delivery = Delivery(
        driver_id=driver_id,
        order_number=order_number,
        delivery_address=delivery_address,
        notes=notes,
        status="pending"
    )
    db.add(delivery)
    db.commit()
    return RedirectResponse(url=f"/delivery/{driver_id}", status_code=303)


# ==========================================
# GPS API (Mobil ilova uchun) - MOVED TO PWA API SECTION
# ==========================================

# OLD API REMOVED - See PWA API section below for new implementation




@app.post("/api/driver/location")
async def update_driver_location(
    driver_code: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    speed: float = Form(0),
    db: Session = Depends(get_db)
):
    """Haydovchi lokatsiyasini yangilash"""
    driver = db.query(Driver).filter(Driver.code == driver_code).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    
    location = DriverLocation(
        driver_id=driver.id,
        latitude=latitude,
        longitude=longitude,
        speed=speed
    )
    db.add(location)
    db.commit()
    return {"status": "ok", "message": "Lokatsiya saqlandi"}


@app.get("/api/agents/locations")
async def get_agents_locations(db: Session = Depends(get_db)):
    """Barcha agentlarning oxirgi joylashuvi"""
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    result = []
    for agent in agents:
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        if last_loc:
            result.append({
                "id": agent.id,
                "name": agent.full_name,
                "code": agent.code,
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.isoformat(),
                "battery": last_loc.battery
            })
    return result


@app.get("/api/drivers/locations")
async def get_drivers_locations(db: Session = Depends(get_db)):
    """Barcha haydovchilarning oxirgi joylashuvi"""
    drivers = db.query(Driver).filter(Driver.is_active == True).all()
    result = []
    for driver in drivers:
        last_loc = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.recorded_at.desc()).first()
        if last_loc:
            result.append({
                "id": driver.id,
                "name": driver.full_name,
                "code": driver.code,
                "vehicle": driver.vehicle_number,
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.isoformat(),
                "speed": last_loc.speed
            })
    return result



# ==========================================
# PWA API ENDPOINTS
# ==========================================

@app.post("/api/agent/login")
async def agent_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Agent login API"""
    try:
        agent = db.query(Agent).filter(Agent.phone == username).first()
        
        if not agent or not agent.is_active:
            return {"success": False, "error": "Agent topilmadi yoki faol emas"}
        
        # Oddiy parol tekshiruvi (hozircha telefon = parol)
        if password != agent.phone:
            return {"success": False, "error": "Parol noto'g'ri"}
        
        # Session token yaratish
        token = create_session_token(agent.id, "agent")
        return {
            "success": True,
            "agent": {
                "id": agent.id,
                "code": agent.code,
                "full_name": agent.full_name,
                "phone": agent.phone,
            },
            "token": token
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/driver/login")
async def driver_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Driver login API"""
    try:
        driver = db.query(Driver).filter(Driver.phone == username).first()
        
        if not driver or not driver.is_active:
            return {"success": False, "error": "Haydovchi topilmadi yoki faol emas"}
        
        # Oddiy parol tekshiruvi
        if password != driver.phone:
            return {"success": False, "error": "Parol noto'g'ri"}
        
        token = create_session_token(driver.id, "driver")
        return {
            "success": True,
            "driver": {
                "id": driver.id,
                "code": driver.code,
                "full_name": driver.full_name,
                "phone": driver.phone,
                "vehicle_number": driver.vehicle_number,
            },
            "token": token
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/agent/location_OLD_DISABLED")
async def agent_location_update_OLD(
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float = Form(None),
    battery: int = Form(None),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Agent location update"""
    try:
        user_data = get_user_from_token(token)
        if not user_data or user_data.get("role") != "agent":
            return {"success": False, "error": "Invalid token"}
        
        agent_id = user_data["user_id"]
        
        location = AgentLocation(
            agent_id=agent_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            battery=battery,
        )
        db.add(location)
        db.commit()
        
        return {"success": True, "location_id": location.id}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


@app.post("/api/driver/location")
async def driver_location_update(
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float = Form(None),
    battery: int = Form(None),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Driver location update"""
    try:
        user_data = get_user_from_token(token)
        if not user_data or user_data.get("role") != "driver":
            return {"success": False, "error": "Invalid token"}
        
        driver_id = user_data["user_id"]
        
        location = DriverLocation(
            driver_id=driver_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            battery=battery,
        )
        db.add(location)
        db.commit()
        
        return {"success": True, "location_id": location.id}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


@app.get("/api/agent/orders")
async def agent_orders(token: str, db: Session = Depends(get_db)):
    """Agent orders list"""
    try:
        user_data = get_user_from_token(token)
        if not user_data:
            return {"success": False, "error": "Invalid token"}
        
        # Hozircha bo'sh ro'yxat qaytaramiz
        return {"success": True, "orders": []}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/agent/partners")
async def agent_partners(token: str, db: Session = Depends(get_db)):
    """Agent partners list"""
    try:
        user_data = get_user_from_token(token)
        if not user_data:
            return {"success": False, "error": "Invalid token"}
        
        partners = db.query(Partner).filter(Partner.is_active == True).all()
        return {
            "success": True,
            "partners": [
                {
                    "id": p.id,
                    "name": p.name,
                    "phone": p.phone,
                    "address": p.address,
                }
                for p in partners
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==========================================
# STARTUP
# ==========================================

# ==========================================
# PWA API ENDPOINTS
# ==========================================

@app.post("/api/agent/location")
async def agent_location_update(
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float = Form(None),
    battery: int = Form(None),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Agent location update"""
    try:
        # Test mode - agent_id = 1
        agent_id = 1
        
        location = AgentLocation(
            agent_id=agent_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            battery=battery,
        )
        db.add(location)
        db.commit()
        
        return {"success": True, "location_id": location.id}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}



# ==========================================
# HUDUDLAR (REGIONS)
# ==========================================

@app.get("/test/regions", response_class=HTMLResponse)
async def regions_test_page(request: Request, db: Session = Depends(get_db)):
    """Hududlar test sahifasi - authentication'siz"""
    regions = db.query(Region).all()
    # Fake user for testing
    fake_user = {"username": "test", "role": "admin"}
    return templates.TemplateResponse("info/regions.html", {
        "request": request,
        "page_title": "Hududlar",
        "user": fake_user,
        "regions": regions
    })


@app.get("/info/regions", response_class=HTMLResponse)
async def regions_page(request: Request, db: Session = Depends(get_db)):
    """Hududlar sahifasi"""
    user = get_user_from_token(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    regions = db.query(Region).all()
    return templates.TemplateResponse("info/regions.html", {
        "request": request,
        "page_title": "Hududlar",
        "user": user,
        "regions": regions
    })


@app.post("/info/regions/add")
async def region_add(
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Hudud qo'shish"""
    existing = db.query(Region).filter(Region.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli hudud allaqachon mavjud!")
    
    region = Region(code=code, name=name, description=description)
    db.add(region)
    db.commit()
    return RedirectResponse(url="/info/regions", status_code=303)


@app.post("/info/regions/edit/{region_id}")
async def region_edit(
    region_id: int,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Hududni tahrirlash"""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Hudud topilmadi")
    
    existing = db.query(Region).filter(
        Region.code == code,
        Region.id != region_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli hudud allaqachon mavjud!")
    
    region.code = code
    region.name = name
    region.description = description
    db.commit()
    return RedirectResponse(url="/info/regions", status_code=303)


@app.post("/info/regions/delete/{region_id}")
async def region_delete(region_id: int, db: Session = Depends(get_db)):
    """Hududni o'chirish"""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Hudud topilmadi")
    
    db.delete(region)
    db.commit()
    return RedirectResponse(url="/info/regions", status_code=303)


@app.on_event("startup")
async def startup():
    """Dastur ishga tushganda"""
    init_db()
    print("рџљЂ TOTLI HOLVA Business System ishga tushdi!")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

