with open('app/templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add JavaScript to force hide sidebar on mobile
js_code = """
    <script>
        // Force hide sidebar on mobile
        if (window.innerWidth <= 768) {
            document.addEventListener('DOMContentLoaded', function() {
                const sidebar = document.querySelector('.sidebar');
                if (sidebar) {
                    sidebar.style.display = 'none';
                    sidebar.style.visibility = 'hidden';
                    sidebar.style.width = '0';
                }
                const mainContent = document.querySelector('.main-content');
                if (mainContent) {
                    mainContent.style.marginLeft = '0';
                    mainContent.style.width = '100%';
                }
            });
        }
    </script>
"""

# Insert before </body>
content = content.replace('</body>', js_code + '\n</body>')

with open('app/templates/base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ JavaScript sidebar fix added!")
