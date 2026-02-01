"""
Test Machine Model
Create sample machines for testing
"""
from app.models.database import get_db, Machine, init_db
from datetime import datetime, timedelta

# Initialize database
init_db()

# Get database session
db = next(get_db())

# Create sample machines
machines = [
    {
        "code": "MIX-001",
        "name": "Mixer #1",
        "machine_type": "mixer",
        "status": "active",
        "capacity": 500.0,
        "efficiency": 95.0
    },
    {
        "code": "MIX-002",
        "name": "Mixer #2",
        "machine_type": "mixer",
        "status": "active",
        "capacity": 500.0,
        "efficiency": 92.0
    },
    {
        "code": "OVN-001",
        "name": "Oven #1",
        "machine_type": "oven",
        "status": "active",
        "capacity": 1000.0,
        "efficiency": 98.0
    },
    {
        "code": "OVN-002",
        "name": "Oven #2",
        "machine_type": "oven",
        "status": "idle",
        "capacity": 1000.0,
        "efficiency": 100.0
    },
    {
        "code": "PKG-001",
        "name": "Packaging #1",
        "machine_type": "packaging",
        "status": "maintenance",
        "capacity": 300.0,
        "efficiency": 85.0,
        "last_maintenance": datetime.now() - timedelta(days=5),
        "next_maintenance": datetime.now() + timedelta(days=25)
    },
    {
        "code": "PKG-002",
        "name": "Packaging #2",
        "machine_type": "packaging",
        "status": "active",
        "capacity": 300.0,
        "efficiency": 90.0
    }
]

print("Creating machines...")
for machine_data in machines:
    # Check if machine already exists
    existing = db.query(Machine).filter(Machine.code == machine_data["code"]).first()
    if existing:
        print(f"  ⏭️  {machine_data['code']} already exists")
        continue
    
    machine = Machine(**machine_data)
    db.add(machine)
    print(f"  ✅ Created {machine_data['code']} - {machine_data['name']}")

db.commit()

# Display summary
total = db.query(Machine).count()
active = db.query(Machine).filter(Machine.status == 'active').count()
idle = db.query(Machine).filter(Machine.status == 'idle').count()
maintenance = db.query(Machine).filter(Machine.status == 'maintenance').count()

print(f"\n📊 Machine Summary:")
print(f"  Total: {total}")
print(f"  Active: {active}")
print(f"  Idle: {idle}")
print(f"  Maintenance: {maintenance}")

db.close()
print("\n✅ Done!")
