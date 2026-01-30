

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
            timestamp=datetime.now()
        )
        db.add(location)
        db.commit()
        
        return {"success": True, "location_id": location.id}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
