# Fix timestamp -> recorded_at
with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Replace timestamp with recorded_at (remove the line)
content = content.replace(
    '            timestamp=datetime.now()\n',
    ''
)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed timestamp!")
