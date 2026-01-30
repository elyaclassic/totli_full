# Disable old API by renaming endpoint
with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Replace first occurrence only
content = content.replace(
    '@app.post("/api/agent/location")\nasync def agent_location_update(',
    '@app.post("/api/agent/location_OLD_DISABLED")\nasync def agent_location_update_OLD(',
    1  # Only first occurrence
)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Old API disabled!")
