with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

with open('pwa_apis.txt', 'r', encoding='utf-8') as f:
    pwa_apis = f.read()

# Insert before "# STARTUP" comment
content = content.replace(
    '# ==========================================\n# STARTUP\n# ==========================================',
    pwa_apis + '\n\n# ==========================================\n# STARTUP\n# =========================================='
)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ PWA APIs added to main.py!")
