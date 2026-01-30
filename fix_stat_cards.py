with open('app/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find mobile CSS section and add stat card fixes
mobile_css_addition = """
            .stat-card {
                padding: 15px !important;
                margin-bottom: 10px !important;
            }

            .stat-card h3 {
                font-size: 1.5rem !important;
                word-break: break-all;
            }

            .stat-card p {
                font-size: 0.75rem !important;
            }

            .stat-card .icon {
                width: 40px !important;
                height: 40px !important;
                font-size: 1.2rem !important;
            }
"""

# Insert before closing of @media (max-width: 768px)
content = content.replace(
    "            .main-content {\n                margin-left: 0 !important;\n            }\n        }",
    f"            .main-content {{\n                margin-left: 0 !important;\n            }}\n{mobile_css_addition}        }}"
)

with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Stat cards fixed for mobile!")
