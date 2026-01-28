"""
Login endpointini test qilish
"""
import requests

url = "http://10.243.45.144:8080/login"
data = {
    "username": "admin",
    "password": "admin123"
}

print("=" * 60)
print("LOGIN TEST")
print("=" * 60)
print(f"URL: {url}")
print(f"Data: {data}")
print()

try:
    response = requests.post(url, data=data, allow_redirects=False)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 303:
        print("✅ Login muvaffaqiyatli! Redirect qilinmoqda...")
        print(f"Location: {response.headers.get('Location')}")
        print(f"Cookies: {response.cookies}")
    else:
        print("❌ Login muvaffaqiyatsiz!")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Xato: {e}")
