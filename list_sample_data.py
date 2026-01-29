"""
Namunaviy ma'lumotlarni ko'rsatish (ASCII)
Show test/sample data in the database
"""

import sqlite3

conn = sqlite3.connect('totli_holva.db')
c = conn.cursor()

print("=" * 60)
print("NAMUNAVIY MA'LUMOTLAR RO'YXATI")
print("=" * 60)

# AGENTLAR
print("\nAGENTLAR (AGENTS)")
print("-" * 60)
c.execute('SELECT id, full_name, phone, region, is_active FROM agents')
agents = c.fetchall()
for row in agents:
    status = "Faol" if row[4] else "Nofaol"
    print(f"{row[0]}. {row[1]}")
    print(f"   Tel: {row[2]}")
    print(f"   Hudud: {row[3]}")
    print(f"   Status: {status}\n")

# HAYDOVCHILAR
print("\nHAYDOVCHILAR (DRIVERS)")
print("-" * 60)
c.execute('SELECT id, full_name, phone, vehicle_number, is_active FROM drivers')
drivers = c.fetchall()
for row in drivers:
    status = "Faol" if row[4] else "Nofaol"
    print(f"{row[0]}. {row[1]}")
    print(f"   Tel: {row[2]}")
    print(f"   Mashina: {row[3]}")
    print(f"   Status: {status}\n")

# MIJOZLAR
print("\nMIJOZLAR (PARTNERS)")
print("-" * 60)
c.execute('SELECT id, name, phone, address FROM partners LIMIT 20')
partners = c.fetchall()
for row in partners:
    print(f"{row[0]}. {row[1]}")
    print(f"   Tel: {row[2] if row[2] else \"Yo'q\"}")
    print(f"   Manzil: {row[3] if row[3] else \"Yo'q\"}\n")

# LOKATSIYALAR
print("\nLOKATSIYALAR")
print("-" * 60)
c.execute('''
    SELECT a.full_name, COUNT(al.id) as loc_count
    FROM agents a
    LEFT JOIN agent_locations al ON a.id = al.agent_id
    GROUP BY a.id
''')
print("Agent lokatsiyalari:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} ta")

c.execute('''
    SELECT d.full_name, COUNT(dl.id) as loc_count
    FROM drivers d
    LEFT JOIN driver_locations dl ON d.id = dl.driver_id
    GROUP BY d.id
''')
print("\nHaydovchi lokatsiyalari:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} ta")

c.execute('SELECT COUNT(*) FROM partner_locations')
count = c.fetchone()[0]
print(f"\nMijoz lokatsiyalari: {count} ta")

# MAHSULOTLAR
print("\n\nMAHSULOTLAR (PRODUCTS)")
print("-" * 60)
c.execute('SELECT COUNT(*) FROM products')
product_count = c.fetchone()[0]
print(f"Jami: {product_count} ta mahsulot\n")

c.execute('SELECT id, name, barcode FROM products LIMIT 10')
for row in c.fetchall():
    print(f"{row[0]}. {row[1]} (Barcode: {row[2] if row[2] else \"Yo'q\"})")

# KATEGORIYALAR
print("\n\nKATEGORIYALAR (CATEGORIES)")
print("-" * 60)
c.execute('SELECT id, name FROM categories')
for row in c.fetchall():
    print(f"{row[0]}. {row[1]}")

# OMBORLAR
print("\n\nOMBORLAR (WAREHOUSES)")
print("-" * 60)
c.execute('SELECT id, name, address FROM warehouses')
for row in c.fetchall():
    print(f"{row[0]}. {row[1]}")
    if row[2]:
        print(f"   Manzil: {row[2]}")

# FOYDALANUVCHILAR
print("\n\nFOYDALANUVCHILAR (USERS)")
print("-" * 60)
c.execute('SELECT id, username, full_name, role, is_active FROM users')
for row in c.fetchall():
    status = "Faol" if row[4] else "Nofaol"
    print(f"{row[0]}. {row[2]} (@{row[1]})")
    print(f"   Rol: {row[3]}")
    print(f"   Status: {status}\n")

print("\n" + "=" * 60)
print("XULOSA")
print("=" * 60)
print(f"Agentlar: {len(agents)} ta")
print(f"Haydovchilar: {len(drivers)} ta")
print(f"Mijozlar: {len(partners)} ta (ko'rsatilgan)")
print(f"Mahsulotlar: {product_count} ta")
print("=" * 60)

conn.close()
