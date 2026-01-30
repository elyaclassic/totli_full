from app.models.database import Agent, SessionLocal
from datetime import datetime

# Create session
db = SessionLocal()

try:
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.phone == "998901234567").first()
    
    if agent:
        print(f"Agent topildi: {agent.full_name}")
        print(f"ID: {agent.id}")
        print(f"Code: {agent.code}")
        print(f"Active: {agent.is_active}")
        
        # Activate if not active
        if not agent.is_active:
            agent.is_active = True
            db.commit()
            print("Agent faollashtirildi!")
    else:
        # Create new agent
        new_agent = Agent(
            code="AG001",
            full_name="Test Agent",
            phone="998901234567",
            is_active=True,
            created_at=datetime.now()
        )
        db.add(new_agent)
        db.commit()
        print(f"Yangi agent yaratildi! ID: {new_agent.id}")
        
except Exception as e:
    print(f"Xato: {e}")
    db.rollback()
finally:
    db.close()
