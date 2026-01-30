import re

with open('main.py', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Find all /api/agent/location endpoints
pattern = r'@app\.post\("/api/agent/location"\)'
matches = re.findall(pattern, content)

print(f'Total /api/agent/location endpoints: {len(matches)}')

# Find line numbers
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if '@app.post("/api/agent/location")' in line:
        print(f'Line {i}: {line.strip()}')
