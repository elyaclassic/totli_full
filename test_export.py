"""
Test script for Excel export
"""
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

# Test export
print("📊 Testing Excel export...")
export_response = s.get('http://localhost:8080/dashboard/executive/export')
print(f"Export status: {export_response.status_code}")

if export_response.status_code == 200:
    # Save file
    with open('test_export.xlsx', 'wb') as f:
        f.write(export_response.content)
    print("✅ Excel file saved: test_export.xlsx")
    print(f"File size: {len(export_response.content)} bytes")
else:
    print(f"❌ Export failed: {export_response.text[:200]}")
