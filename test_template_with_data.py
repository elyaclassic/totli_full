"""
Test Jinja2 template rendering with actual data
"""
from jinja2 import Template, Environment, FileSystemLoader
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.models.database import SessionLocal, Agent, Driver, AgentLocation, DriverLocation, PartnerLocation

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
    # Database'dan ma'lumot olish
    db = SessionLocal()
    
    # Agentlarni olish
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    for agent in agents:
        agent.locations = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).limit(1).all()
    
    # Haydovchilarni olish
    drivers = db.query(Driver).filter(Driver.is_active == True).all()
    for driver in drivers:
        driver.locations = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.recorded_at.desc()).limit(1).all()
    
    # Mijozlar
    partner_locations = db.query(PartnerLocation).all()
    
    print(f"Agents: {len(agents)}")
    print(f"Agents with locations: {len([a for a in agents if a.locations])}")
    print(f"Drivers: {len(drivers)}")
    print(f"Drivers with locations: {len([d for d in drivers if d.locations])}")
    print(f"Partner locations: {len(partner_locations)}")
    
    # Template'ni yuklash
    template = env.get_template('map/index.html')
    print("\n✅ Template loaded!")
    
    # Render qilish
    html = template.render(
        agents=agents,
        drivers=drivers,
        partner_locations=partner_locations,
        user={'username': 'test'},
        page_title='Xarita'
    )
    print("✅ Template rendered successfully!")
    print(f"HTML length: {len(html)} bytes")
    
    # JavaScript qismini chiqarish
    script_start = html.find('<script>')
    script_end = html.find('</script>', script_start)
    if script_start != -1 and script_end != -1:
        script = html[script_start:script_end + 9]
        print("\n=== GENERATED JAVASCRIPT ===")
        print(script[:2000])  # Birinchi 2000 belgi
    
    db.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
