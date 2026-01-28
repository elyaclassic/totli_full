"""
Barcha sahifalarni himoyalash uchun helper skript
"""
import re

# main.py ni o'qish
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Barcha @app.get endpointlarni topish (login va logout dan tashqari)
pattern = r'@app\.get\("(/[^"]+)"\s*,\s*response_class=HTMLResponse\)\s*\nasync def (\w+)\(request: Request'

matches = re.findall(pattern, content)

print("Himoyalanmagan sahifalar:")
print("=" * 60)
for path, func_name in matches:
    if 'login' not in path and 'logout' not in path:
        print(f"{path:40} -> {func_name}")
