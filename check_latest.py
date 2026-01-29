import sqlite3

conn = sqlite3.connect('totli_holva.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM agent_locations')
total = c.fetchone()[0]
print(f'Jami agent lokatsiyalari: {total} ta')

print('\nOXIRGI 5 TA LOKATSIYA:')
print('-' * 80)

c.execute('''
    SELECT al.id, a.full_name, al.latitude, al.longitude, al.battery, al.recorded_at
    FROM agent_locations al
    JOIN agents a ON al.agent_id = a.id
    ORDER BY al.id DESC
    LIMIT 5
''')

for row in c.fetchall():
    print(f'ID: {row[0]}')
    print(f'Agent: {row[1]}')
    print(f'Koordinatalar: {row[2]:.6f}, {row[3]:.6f}')
    print(f'Battery: {row[4]}%')
    print(f'Vaqt: {row[5]}')
    print('-' * 40)

conn.close()
