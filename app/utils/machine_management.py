"""
Machine Management Routes
CRUD operations for production machines
"""

from fastapi import Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db, Machine, Employee


async def list_machines(request: Request, db: Session):
    """List all machines"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    machines = db.query(Machine).order_by(Machine.created_at.desc()).all()
    
    return {
        "machines": machines,
        "total": len(machines),
        "active": sum(1 for m in machines if m.is_active),
        "in_operation": sum(1 for m in machines if m.status == 'active'),
        "maintenance": sum(1 for m in machines if m.status == 'maintenance')
    }


async def create_machine(request: Request, db: Session, 
                        code: str, name: str, machine_type: str,
                        capacity: float = 0, efficiency: float = 100.0):
    """Create new machine"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    machine = Machine(
        code=code,
        name=name,
        machine_type=machine_type,
        capacity=capacity,
        efficiency=efficiency,
        status="idle"
    )
    
    db.add(machine)
    db.commit()
    db.refresh(machine)
    
    return machine


async def update_machine_status(request: Request, db: Session,
                               machine_id: int, status: str,
                               operator_id: int = None):
    """Update machine status"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/login", status_code=303)
    
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        return None
    
    machine.status = status
    if operator_id:
        machine.operator_id = operator_id
    
    db.commit()
    db.refresh(machine)
    
    return machine
