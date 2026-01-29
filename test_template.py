"""
Test Jinja2 template syntax
"""
from jinja2 import Template, Environment, FileSystemLoader
import os

# Template papkasini sozlash
template_dir = os.path.join(os.path.dirname(__file__), 'app', 'templates')
env = Environment(
    loader=FileSystemLoader(template_dir),
    block_start_string='{%',
    block_end_string='%}',
    variable_start_string='{{',
    variable_end_string='}}',
    comment_start_string='{#',
    comment_end_string='#}',
)

try:
    # Template'ni yuklash
    template = env.get_template('map/index.html')
    print("✅ Template syntax OK!")
    
    # Test ma'lumotlar bilan render qilish
    html = template.render(
        agents=[],
        drivers=[],
        partner_locations=[],
        user={'username': 'test'},
        page_title='Xarita'
    )
    print("✅ Template rendered successfully!")
    print(f"HTML length: {len(html)} bytes")
    
except Exception as e:
    print(f"❌ Template error: {e}")
    import traceback
    traceback.print_exc()
