"""
Login test - oddiy HTTP so'rov
"""
import urllib.request
import urllib.parse

url = "http://127.0.0.1:8080/login"
data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()

print("=" * 60)
print("LOGIN TEST")
print("=" * 60)

try:
    req = urllib.request.Request(url, data=data, method="POST")
    
    # Redirect ni kuzatmaslik
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    
    opener = urllib.request.build_opener(NoRedirect)
    
    try:
        response = opener.open(req)
        print(f"✅ Status: {response.status}")
        print(f"✅ Headers: {dict(response.headers)}")
    except urllib.error.HTTPError as e:
        if e.code == 303:
            print(f"✅ LOGIN MUVAFFAQIYATLI! Redirect: {e.code}")
            print(f"✅ Location: {e.headers.get('Location')}")
            print(f"✅ Cookies: {e.headers.get('Set-Cookie')}")
        else:
            print(f"❌ HTTP Error: {e.code}")
            print(f"❌ Response: {e.read().decode()[:500]}")
            
except Exception as e:
    print(f"❌ Xato: {e}")
    import traceback
    traceback.print_exc()
