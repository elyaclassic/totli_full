"""
Dashboard sahifalari: rahbariyat, savdo, agent, ishlab chiqarish, ombor, yetkazib berish.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core import templates
from app.models.database import (
    get_db,
    User,
    Order,
    OrderItem,
    Product,
    Partner,
    Agent,
    AgentLocation,
    Stock,
    Category,
    Purchase,
    PurchaseItem,
    Production,
    Recipe,
    Employee,
    Delivery,
    Driver,
    DriverLocation,
    Visit,
)
from app.deps import require_auth, require_admin
from app.utils.dashboard_export import export_executive_dashboard
from app.utils.live_data import executive_live_data, warehouse_live_data, delivery_live_data

router = APIRouter(tags=["dashboards"])


# ==========================================
# DASHBOARDS
# ==========================================

# Test route without authentication
@router.get("/test/dashboard/executive", response_class=HTMLResponse)
async def executive_dashboard_test(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Rahbariyat Dashboard - Test (fake data), faqat admin"""
    
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
        "current_user": None,
        "user": fake_user,
        "stats": stats,
        "sales_trend": sales_trend,
        "top_products": top_products,
        "top_agents": top_agents,
        "alerts": alerts
    })


@router.get("/dashboard/executive", response_class=HTMLResponse)
async def executive_dashboard(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Rahbariyat Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Order, OrderItem, Agent, Stock, Product
    
    if not current_user:
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
        func.sum(Stock.quantity * Product.purchase_price)
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
        "current_user": current_user,
        "user": current_user,
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


# Executive Dashboard - Export to Excel
@router.get("/dashboard/executive/export")
async def executive_export(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Export Executive Dashboard to Excel"""
    return await export_executive_dashboard(request, db)


# Live Data Endpoints
@router.get("/dashboard/executive/live")
async def executive_live(request: Request, db: Session = Depends(get_db)):
    """Live data for Executive Dashboard"""
    return await executive_live_data(request, db)

@router.get("/dashboard/warehouse/live")
async def warehouse_live(request: Request, db: Session = Depends(get_db)):
    """Live data for Warehouse Dashboard"""
    return await warehouse_live_data(request, db)

@router.get("/dashboard/delivery/live")
async def delivery_live(request: Request, db: Session = Depends(get_db)):
    """Live data for Delivery Dashboard"""
    return await delivery_live_data(request, db)


# Sales Dashboard - Real Data
@router.get("/dashboard/sales", response_class=HTMLResponse)
async def sales_dashboard(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Savdo Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Order, Partner
    
    if not current_user:
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
        "current_user": current_user,
        "user": current_user,
        "metrics": metrics,
        "order_status": order_status,
        "funnel": funnel,
        "weekly_sales": weekly_sales,
        "recent_orders": recent_orders,
        "top_customers": top_customers
    })


# Sales Dashboard - Test (fake data)
@router.get("/test/dashboard/sales", response_class=HTMLResponse)
async def sales_dashboard_test(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Savdo Dashboard - Test (fake data), faqat admin"""
    
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
@router.get("/dashboard/agent", response_class=HTMLResponse)
async def agent_dashboard(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Agent Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Agent, Visit, Route, RoutePoint, Partner, Order, AgentLocation
    
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Get agent for current user (assuming user has agent_id or we use first agent)
    agent = db.query(Agent).filter(Agent.is_active == True).first()
    if not agent:
        # No agent found - show empty dashboard
        agent = {'name': 'Agent topilmadi', 'location': '-'}
        return templates.TemplateResponse("dashboards/agent.html", {
            "request": request,
            "page_title": "Agent Dashboard",
            "current_user": current_user,
            "user": current_user,
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
        "current_user": current_user,
        "user": current_user,
        "agent": agent_info,
        "kpi": kpi,
        "schedule": schedule,
        "recent_orders": recent_orders,
        "customers": customers,
        "performance": performance
    })


# Agent Dashboard - Test (fake data)
@router.get("/test/dashboard/agent", response_class=HTMLResponse)
async def agent_dashboard_test(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Agent Dashboard - Test (fake data), faqat admin"""
    
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
        "current_user": None,
        "user": fake_user,
        "agent": agent,
        "kpi": kpi,
        "schedule": schedule,
        "recent_orders": recent_orders,
        "customers": customers,
        "performance": performance
    })



# Production Dashboard - Real Data
@router.get("/dashboard/production", response_class=HTMLResponse)
async def production_dashboard(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Ishlab chiqarish Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Production, Recipe, Product, Employee
    
    if not current_user:
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
        "current_user": current_user,
        "user": current_user,
        "metrics": metrics,
        "production_orders": production_orders,
        "machines": machines,
        "chart": chart
    })


# Production Dashboard - Test (fake data)
@router.get("/test/dashboard/production", response_class=HTMLResponse)
async def production_dashboard_test(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Ishlab chiqarish Dashboard - Test (fake data), faqat admin"""
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
        "current_user": None,
        "user": fake_user,
        "metrics": metrics,
        "production_orders": production_orders,
        "machines": machines,
        "chart": chart
    })


# Warehouse Dashboard - Real Data
@router.get("/dashboard/warehouse", response_class=HTMLResponse)
async def warehouse_dashboard(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Ombor Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.database import Stock, Product, Category, Purchase, PurchaseItem
    
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Total warehouse value
    total_value = db.query(
        func.sum(Stock.quantity * Product.purchase_price)
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
        "current_user": current_user,
        "user": current_user,
        "metrics": metrics,
        "low_stock": low_stock,
        "recent_moves": recent_moves,
        "chart": chart
    })


# Warehouse Dashboard - Test (fake data)
@router.get("/test/dashboard/warehouse", response_class=HTMLResponse)
async def warehouse_dashboard_test(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Ombor Dashboard - Test (fake data), faqat admin"""
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
@router.get("/dashboard/delivery", response_class=HTMLResponse)
async def delivery_dashboard(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Yetkazib berish Dashboard - Real Data"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, case
    from app.models.database import Delivery, Driver, DriverLocation, Order, Partner
    
    if not current_user:
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
        "current_user": current_user,
        "user": current_user,
        "metrics": metrics,
        "deliveries": deliveries,
        "drivers": drivers,
        "chart": chart
    })


# Delivery Dashboard - Test (fake data)
@router.get("/test/dashboard/delivery", response_class=HTMLResponse)
async def delivery_dashboard_test(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Yetkazib berish Dashboard - Test (fake data), faqat admin"""
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
