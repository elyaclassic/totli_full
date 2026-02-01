"""
Agent visit API endpoints
"""
from fastapi import Form, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db, Visit
from app.utils.auth import get_user_from_token


async def agent_visit_start(
    partner_id: int = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float = Form(...),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Agent tashrif boshlash"""
    try:
        # TEMPORARY TEST MODE - bypass token validation
        agent_id = 1  # Hardcoded for testing
        
        # Get agent_id from token (commented out for now)
        # user_data = get_user_from_token(token)
        # if not user_data or user_data.get('user_type') != 'agent':
        #     return {"success": False, "error": "Invalid token"}
        # agent_id = user_data.get('user_id')
        
        # Create visit record
        visit = Visit(
            agent_id=agent_id,
            partner_id=partner_id,
            visit_date=datetime.now(),
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            status='in_progress'
        )
        db.add(visit)
        db.commit()
        
        return {
            "success": True,
            "visit_id": visit.id,
            "message": "Tashrif boshlandi"
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
