# Fix main.py - remove corrupted lines
with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Keep only first 2689 lines (before corruption)
with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines[:2689])

print(f"Fixed! Total lines: {len(lines[:2689])}")
