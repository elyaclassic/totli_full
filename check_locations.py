import sqlite3
from datetime import datetime

conn = sqlite3.connect('totli_holva.db')
c = conn.cursor()

print("=" * 80)
print("OXIRGI AGENT LOKATSIYALARI")
print("=" * 80)

c.execute('''
    SELECT al.id, a.full_name, al.latitude, al.longitude, al.battery, al.recorded_at
    FROM agent_locations al
    JOIN agents a ON al.agent_id = a.id
    ORDER BY al.recorded_at DESC
    LIMIT 10
''')

for row in c.fetchall():
    print(f"\nID: {row[0]}")
    print(f"Agent: {row[1]}")
    print(f"Latitude: {row[2]:.6f}")
    print(f"Longitude: {row[3]:.6f}")
    print(f"Battery: {row[4]}%")
    print(f"Vaqt: {row[5]}")
    print("-" * 40)

print("\n" + "=" * 80)
print("OXIRGI DRIVER LOKATSIYALARI")
print("=" * 80)

c.execute('''
    SELECT dl.id, d.full_name, dl.latitude, dl.longitude, dl.battery, dl.recorded_at
    FROM driver_locations dl
    JOIN drivers d ON dl.driver_id = d.id
    ORDER BY dl.recorded_at DESC
    LIMIT 10
''')

for row in c.fetchall():
    print(f"\nID: {row[0]}")
    print(f"Driver: {row[1]}")
    print(f"Latitude: {row[2]:.6f}")
    print(f"Longitude: {row[3]:.6f}")
    print(f"Battery: {row[4]}%")
    print(f"Vaqt: {row[5]}")
    print("-" * 40)

# Statistika
print("\n" + "=" * 80)
print("STATISTIKA")
print("=" * 80)

c.execute('SELECT COUNT(*) FROM agent_locations')
agent_count = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM driver_locations')
driver_count = c.fetchone()[0]

print(f"Jami agent lokatsiyalari: {agent_count}")
print(f"Jami driver lokatsiyalari: {driver_count}")

# Bugungi lokatsiyalar
today = datetime.now().date()
c.execute('SELECT COUNT(*) FROM agent_locations WHERE DATE(recorded_at) = ?', (today,))
today_agent = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM driver_locations WHERE DATE(recorded_at) = ?', (today,))
today_driver = c.fetchone()[0]

print(f"\nBugungi agent lokatsiyalari: {today_agent}")
print(f"Bugungi driver lokatsiyalari: {today_driver}")

conn.close()
