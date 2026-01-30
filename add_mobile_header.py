with open('app/templates/base.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find <body> tag (around line 290)
for i, line in enumerate(lines):
    if '<body>' in line:
        # Insert mobile header after <body>
        lines.insert(i + 1, '''    <!-- Mobile Header -->
    <div class="mobile-header">
        <div class="hamburger" onclick="toggleSidebar()">
            <i class="bi bi-list"></i>
        </div>
        <div class="title">TOTLI HOLVA</div>
        <div class="user-menu">
            <i class="bi bi-person-circle"></i>
        </div>
    </div>

''')
        break

with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Mobile header added!")
