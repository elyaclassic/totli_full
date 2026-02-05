"""
Reja (scheduler) — kunlik/vaqtli vazifalar.
Kam qolgan tovar va muddati o'tgan qarzlar uchun bildirishnoma yaratadi.
"""

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from app.models.database import SessionLocal, Order
from app.utils.notifications import check_low_stock_and_notify, create_notification


def _scheduled_notifications_job():
    """Har ishga tushganda: kam qoldiq tekshiruvi va muddati o'tgan qarzlar bildirishnomasi."""
    db = SessionLocal()
    try:
        # 1) Kam qolgan tovarlar
        n_low = check_low_stock_and_notify(db)
        # 2) Muddati o'tgan qarzlar (sotuvda qarz > 0, 7+ kun oldin)
        overdue_cutoff = datetime.now() - timedelta(days=7)
        overdue = db.query(Order).filter(
            Order.type == "sale",
            Order.debt > 0,
            Order.created_at < overdue_cutoff,
        ).all()
        if overdue:
            total_debt = sum(o.debt for o in overdue)
            create_notification(
                db,
                title="Muddati o'tgan qarzlar",
                message=f"{len(overdue)} ta buyurtmada jami {total_debt:,.0f} so'm qarz muddati o'tgan (7+ kun).",
                notification_type="warning",
                priority="high",
                action_url="/reports/debts",
                related_entity_type="order",
            )
    except Exception as e:
        print(f"[Scheduler] xato: {e}")
    finally:
        db.close()


_scheduler = None


def start_scheduler():
    """Scheduler ni ishga tushiradi — har 6 soatda bildirishnomalar."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_scheduled_notifications_job, "interval", hours=6, id="notifications")
    _scheduler.add_job(_scheduled_notifications_job, "date", run_date=datetime.now() + timedelta(minutes=1), id="notifications_first")
    _scheduler.start()
    print("[Scheduler] Reja ishga tushdi (har 6 soatda kam qoldiq va qarz eslatmasi)")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
