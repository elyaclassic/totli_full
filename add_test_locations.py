"""
Mavjud agent va driverlarga lokatsiya qo'shish
"""
import sqlite3
from datetime import datetime

def add_locations():
    conn = sqlite3.connect('totli_holva.db')
    cursor = conn.cursor()
    
    try:
        # Mavjud agentlarni olish
        cursor.execute("SELECT id FROM agents WHERE is_active = 1 LIMIT 4")
        agents = cursor.fetchall()
        
        # Toshkent atrofidagi turli lokatsiyalar
        locations = [
            (41.311081, 69.240562, 85),  # Toshkent markazi
            (41.275230, 69.203430, 92),  # Chilonzor
            (41.350000, 69.289000, 78),  # Yunusobod
            (41.220000, 69.220000, 95),  # Sergeli
        ]
        
        # Har bir agentga lokatsiya qo'shish
        for i, agent in enumerate(agents):
            lat, lon, battery = locations[i % len(locations)]
            cursor.execute("""
                INSERT INTO agent_locations (agent_id, latitude, longitude, battery, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            """, (agent[0], lat, lon, battery, datetime.now()))
            print(f"✅ Agent {agent[0]} uchun lokatsiya qo'shildi: ({lat}, {lon})")
        
        # Mavjud driverlarni olish
        cursor.execute("SELECT id FROM drivers WHERE is_active = 1 LIMIT 4")
        drivers = cursor.fetchall()
        
        # Driver lokatsiyalari (tezlik bilan)
        driver_locs = [
            (41.326418, 69.228387, 45.5),  # Amir Temur
            (41.299496, 69.240073, 32.0),  # Mirzo Ulugbek
            (41.285000, 69.260000, 55.3),  # Yashnobod
            (41.340000, 69.210000, 28.7),  # Mirobod
        ]
        
        # Har bir driverga lokatsiya qo'shish
        for i, driver in enumerate(drivers):
            lat, lon, speed = driver_locs[i % len(driver_locs)]
            cursor.execute("""
                INSERT INTO driver_locations (driver_id, latitude, longitude, speed, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            """, (driver[0], lat, lon, speed, datetime.now()))
            print(f"✅ Driver {driver[0]} uchun lokatsiya qo'shildi: ({lat}, {lon}), {speed} km/h")
        
        conn.commit()
        print(f"\n🎉 Jami {len(agents)} ta agent va {len(drivers)} ta driver uchun lokatsiyalar qo'shildi!")
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_locations()
