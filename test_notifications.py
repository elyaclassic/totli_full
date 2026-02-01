"""
Test Notification System
Create sample notifications
"""
from app.models.database import get_db, init_db
from app.utils.notifications import (
    create_notification,
    create_low_stock_notification,
    create_order_notification,
    create_delivery_notification,
    get_user_notifications,
    get_unread_count
)

# Initialize database
init_db()

# Get database session
db = next(get_db())

print("Creating sample notifications...\n")

# 1. Low stock notifications
print("1. Low Stock Notifications:")
create_low_stock_notification(db, "Shokolad", 5, 20)
print("  ✅ Low stock: Shokolad")

create_low_stock_notification(db, "Un", 15, 50)
print("  ✅ Low stock: Un")

# 2. Order notifications
print("\n2. Order Notifications:")
create_order_notification(db, "ORD-001", "Anvar Toshmatov", 450000)
print("  ✅ New order: ORD-001")

create_order_notification(db, "ORD-002", "Dilshod Karimov", 320000)
print("  ✅ New order: ORD-002")

# 3. Delivery notifications
print("\n3. Delivery Notifications:")
create_delivery_notification(db, "DEL-001", "delivered")
print("  ✅ Delivery: DEL-001 delivered")

create_delivery_notification(db, "DEL-002", "in_progress")
print("  ✅ Delivery: DEL-002 in progress")

# 4. General notifications
print("\n4. General Notifications:")
create_notification(
    db=db,
    title="🎉 Yangi xususiyat",
    message="Excel export funksiyasi qo'shildi!",
    notification_type="info",
    priority="low"
)
print("  ✅ Info: New feature")

create_notification(
    db=db,
    title="⚙️ Texnik xizmat",
    message="Tizim bugun kechqurun 22:00 da yangilanadi",
    notification_type="warning",
    priority="high"
)
print("  ✅ Warning: Maintenance")

# Get all notifications
print("\n📊 Notification Summary:")
all_notifications = get_user_notifications(db, user_id=1, limit=100)
print(f"  Total: {len(all_notifications)}")

unread_count = get_unread_count(db, user_id=1)
print(f"  Unread: {unread_count}")

# Display recent notifications
print("\n📬 Recent Notifications:")
for notif in all_notifications[:5]:
    icon = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌'
    }.get(notif.notification_type, '📌')
    
    print(f"  {icon} {notif.title}")
    print(f"     {notif.message}")
    print(f"     Priority: {notif.priority}, Read: {notif.is_read}")
    print()

db.close()
print("✅ Done!")
