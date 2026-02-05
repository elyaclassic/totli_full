"""
Live Data Endpoints
Real-time data updates for dashboards
"""

from fastapi import Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func

from app.models.database import (
    get_db, Order, Stock, Delivery, Production, Notification, Product
)


async def executive_live_data(request: Request, db: Session):
    """Live data for Executive Dashboard"""
    
    today = datetime.now().date()
    
    # Today's sales
    today_sales = db.query(func.sum(Order.total)).filter(
        func.date(Order.created_at) == today,
        Order.status == 'completed'
    ).scalar() or 0
    
    # Today's orders
    today_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0
    
    # Unread notifications
    unread_notifications = db.query(func.count(Notification.id)).filter(
        Notification.is_read == False
    ).scalar() or 0
    
    return JSONResponse({
        "today_sales": float(today_sales),
        "today_orders": today_orders,
        "unread_notifications": unread_notifications,
        "timestamp": datetime.now().isoformat()
    })


async def warehouse_live_data(request: Request, db: Session):
    """Live data for Warehouse Dashboard"""
    
    # Low stock count: Stock.quantity < Product.min_stock (Stock da min_quantity yo'q)
    low_stock = db.query(func.count(Stock.id)).join(Product, Stock.product_id == Product.id).filter(
        Stock.quantity < Product.min_stock
    ).scalar() or 0
    
    # Total products
    total_products = db.query(func.count(Stock.id)).scalar() or 0
    
    return JSONResponse({
        "low_stock": low_stock,
        "total_products": total_products,
        "timestamp": datetime.now().isoformat()
    })


async def delivery_live_data(request: Request, db: Session):
    """Live data for Delivery Dashboard"""
    
    today = datetime.now().date()
    
    # Today's deliveries
    today_deliveries = db.query(func.count(Delivery.id)).filter(
        func.date(Delivery.created_at) == today
    ).scalar() or 0
    
    # Completed deliveries
    completed = db.query(func.count(Delivery.id)).filter(
        func.date(Delivery.created_at) == today,
        Delivery.status == 'delivered'
    ).scalar() or 0
    
    return JSONResponse({
        "today_deliveries": today_deliveries,
        "completed": completed,
        "completion_rate": round((completed / today_deliveries * 100) if today_deliveries > 0 else 0, 1),
        "timestamp": datetime.now().isoformat()
    })
