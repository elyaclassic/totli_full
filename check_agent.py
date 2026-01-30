from app.models.database import Agent, SessionLocal

db = SessionLocal()

try:
    # Find agent by phone
    agent = db.query(Agent).filter(Agent.phone == "998901234567").first()
    
    if agent:
        print(f"✅ Agent topildi:")
        print(f"   ID: {agent.id}")
        print(f"   Code: {agent.code}")
        print(f"   Name: {agent.full_name}")
        print(f"   Phone: {agent.phone}")
        print(f"   Active: {agent.is_active}")
        
        if not agent.is_active:
            agent.is_active = True
            db.commit()
            print("✅ Agent faollashtirildi!")
        else:
            print("✅ Agent allaqachon faol!")
    else:
        print("❌ Agent topilmadi!")
        print("\nBarcha agentlar:")
        agents = db.query(Agent).all()
        for a in agents:
            print(f"  - {a.code}: {a.full_name} ({a.phone}) - Active: {a.is_active}")
        
except Exception as e:
    print(f"❌ Xato: {e}")
finally:
    db.close()
