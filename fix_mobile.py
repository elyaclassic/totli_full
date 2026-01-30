with open('app/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace mobile CSS
old_css = """        @media (max-width: 768px) {
            .sidebar {
                width: 100%;
                height: auto;
                position: relative;
            }

            .main-content {
                margin-left: 0;
            }
        }"""

new_css = """        @media (max-width: 768px) {
            .sidebar {
                display: none !important;
            }

            .main-content {
                margin-left: 0 !important;
            }
        }"""

content = content.replace(old_css, new_css)

with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Mobile CSS updated!")
