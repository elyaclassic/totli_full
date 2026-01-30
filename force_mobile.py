with open('app/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the mobile CSS and make it more aggressive
old_mobile = """        @media (max-width: 768px) {
            .sidebar {
                display: none !important;
            }

            .main-content {
                margin-left: 0 !important;
            }"""

new_mobile = """        /* MOBILE RESPONSIVE - FORCED */
        @media screen and (max-width: 768px) {
            .sidebar {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                width: 0 !important;
                overflow: hidden !important;
            }

            .main-content {
                margin-left: 0 !important;
                width: 100% !important;
                padding: 10px !important;
            }"""

content = content.replace(old_mobile, new_mobile)

with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Aggressive mobile CSS applied!")
