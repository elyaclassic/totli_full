"""Create Agent/Driver rows so PWA login can find them by phone."""
from sqlalchemy.orm import Session

from app.models.database import Agent, Driver


def _next_code(db: Session, model, prefix: str) -> str:
    n = (db.query(model).count() or 0) + 1
    for _ in range(1000):
        code = f"{prefix}{n:03d}"
        if not db.query(model).filter(model.code == code).first():
            return code
        n += 1
    return f"{prefix}{n:03d}"


def _pick_code(db: Session, model, prefix: str, requested: str):
    code = (requested or "").strip() or None
    if code and db.query(model).filter(model.code == code).first():
        code = None
    return code or _next_code(db, model, prefix)


def ensure_agent(db: Session, full_name: str, phone: str, code: str = None, is_active: bool = True, employee_id: int = None):
    """Return the Agent that PWA login will match, creating one when needed."""
    phone = (phone or "").strip()
    if not phone:
        return None
    existing = db.query(Agent).filter(Agent.phone == phone).first()
    if existing:
        if employee_id and not existing.employee_id:
            existing.employee_id = employee_id
        if is_active is False:
            existing.is_active = False
        return existing
    agent = Agent(
        code=_pick_code(db, Agent, "AG", code),
        full_name=(full_name or "").strip() or phone,
        phone=phone,
        is_active=True if is_active is None else bool(is_active),
        employee_id=employee_id,
    )
    db.add(agent)
    db.flush()
    return agent


def ensure_driver(
    db: Session,
    full_name: str,
    phone: str,
    code: str = None,
    is_active: bool = True,
    employee_id: int = None,
    vehicle_number: str = None,
    vehicle_type: str = None,
):
    """Return the Driver that PWA login will match, creating one when needed."""
    phone = (phone or "").strip()
    if not phone:
        return None
    existing = db.query(Driver).filter(Driver.phone == phone).first()
    if existing:
        if employee_id and not existing.employee_id:
            existing.employee_id = employee_id
        if vehicle_number and not existing.vehicle_number:
            existing.vehicle_number = vehicle_number
        if vehicle_type and not existing.vehicle_type:
            existing.vehicle_type = vehicle_type
        if is_active is False:
            existing.is_active = False
        return existing
    driver = Driver(
        code=_pick_code(db, Driver, "DR", code),
        full_name=(full_name or "").strip() or phone,
        phone=phone,
        vehicle_number=(vehicle_number or "").strip() or None,
        vehicle_type=(vehicle_type or "").strip() or None,
        is_active=True if is_active is None else bool(is_active),
        employee_id=employee_id,
    )
    db.add(driver)
    db.flush()
    return driver
