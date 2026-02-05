"""
Notification System
Create and manage system notifications
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import Notification, Stock, Product


def create_notification(db: Session, title: str, message: str,
                       notification_type: str = "info",
                       user_id: int = None,
                       priority: str = "normal",
                       action_url: str = None,
                       related_entity_type: str = None,
                       related_entity_id: int = None,
                       expires_in_days: int = 7):
    """Create a new notification"""
    
    expires_at = datetime.now() + timedelta(days=expires_in_days) if expires_in_days else None
    
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        expires_at=expires_at
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification


def get_user_notifications(db: Session, user_id: int, unread_only: bool = False, limit: int = 10):
    """Get notifications for a specific user"""
    
    query = db.query(Notification).filter(
        (Notification.user_id == user_id) | (Notification.user_id == None)
    )
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    # Filter out expired notifications
    query = query.filter(
        (Notification.expires_at == None) | (Notification.expires_at > datetime.now())
    )
    
    notifications = query.order_by(
        Notification.priority.desc(),
        Notification.created_at.desc()
    ).limit(limit).all()
    
    return notifications


def mark_as_read(db: Session, notification_id: int):
    """Mark notification as read"""
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification:
        notification.is_read = True
        notification.read_at = datetime.now()
        db.commit()
        db.refresh(notification)
    
    return notification


def get_unread_count(db: Session, user_id: int):
    """Get count of unread notifications"""
    
    count = db.query(Notification).filter(
        (Notification.user_id == user_id) | (Notification.user_id == None),
        Notification.is_read == False,
        (Notification.expires_at == None) | (Notification.expires_at > datetime.now())
    ).count()
    
    return count


def create_low_stock_notification(db: Session, product_name: str, quantity: float, min_quantity: float, product_id: Optional[int] = None):
    """Create notification for low stock"""
    return create_notification(
        db=db,
        title="⚠️ Kam qoldiq ogohlantirishi",
        message=f"{product_name} mahsulotidan faqat {quantity:,.0f} qoldi (minimal: {min_quantity:,.0f})",
        notification_type="warning",
        priority="high",
        action_url="/warehouse",
        related_entity_type="stock",
        related_entity_id=product_id,
    )


def check_low_stock_and_notify(db: Session, warehouse_id: Optional[int] = None) -> int:
    """Kirim/sotuv/production tasdiqdan keyin chaqiriladi: kam qolgan tovarlar uchun bildirishnoma yaratadi.
    Bir xil mahsulot uchun 24 soat ichida takroriy bildirishnoma yaratilmaydi.
    Qaytaradi: yaratilgan bildirishnomalar soni."""
    low_stocks = db.query(Stock).join(Product, Stock.product_id == Product.id).filter(
        Stock.quantity < Product.min_stock,
        Product.is_active == True,
    )
    if warehouse_id is not None:
        low_stocks = low_stocks.filter(Stock.warehouse_id == warehouse_id)
    low_stocks = low_stocks.all()
    created = 0
    since = datetime.now() - timedelta(hours=24)
    for stock in low_stocks:
        existing = db.query(Notification).filter(
            Notification.related_entity_type == "stock",
            Notification.related_entity_id == stock.product_id,
            Notification.is_read == False,
            Notification.created_at >= since,
        ).first()
        if not existing and stock.product:
            create_low_stock_notification(
                db,
                product_name=stock.product.name,
                quantity=stock.quantity,
                min_quantity=stock.product.min_stock,
                product_id=stock.product_id,
            )
            created += 1
    return created


def create_order_notification(db: Session, order_number: str, customer_name: str, total: float):
    """Create notification for new order"""
    
    return create_notification(
        db=db,
        title="🛒 Yangi buyurtma",
        message=f"{customer_name} - {order_number} ({total:,.0f} so'm)",
        notification_type="success",
        priority="normal",
        action_url=f"/orders/{order_number}",
        related_entity_type="order"
    )


def create_delivery_notification(db: Session, delivery_number: str, status: str):
    """Create notification for delivery status"""
    
    status_map = {
        'delivered': ('✅ Yetkazildi', 'success'),
        'failed': ('❌ Yetkazilmadi', 'error'),
        'in_progress': ('🚚 Yo\'lda', 'info')
    }
    
    title, notif_type = status_map.get(status, ('📦 Yetkazish yangilandi', 'info'))
    
    return create_notification(
        db=db,
        title=title,
        message=f"Yetkazish #{delivery_number}",
        notification_type=notif_type,
        priority="normal",
        action_url="/dashboard/delivery",
        related_entity_type="delivery"
    )


def cleanup_old_notifications(db: Session, days: int = 30):
    """Delete old read notifications"""
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    deleted = db.query(Notification).filter(
        Notification.is_read == True,
        Notification.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return deleted
