import requests

# Create session
s = requests.Session()

# Login
print("🔐 Logging in...")
login_response = s.post('http://localhost:8080/login', data={
    'username': 'admin',
    'password': 'admin123'
})
print(f"Login status: {login_response.status_code}\n")

# Test ALL dashboards
dashboards = {
    'Executive': '/dashboard/executive',
    'Sales': '/dashboard/sales',
    'Agent': '/dashboard/agent',
    'Production': '/dashboard/production',
    'Warehouse': '/dashboard/warehouse',
    'Delivery': '/dashboard/delivery'
}

print("📊 Testing ALL dashboards:")
print("=" * 40)
for name, url in dashboards.items():
    r = s.get(f'http://localhost:8080{url}')
    status_icon = "✅" if r.status_code == 200 else "❌"
    print(f"{status_icon} {name:15} {r.status_code}")
print("=" * 40)
