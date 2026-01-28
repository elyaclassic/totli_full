"""
Test home page with cookie
"""
import urllib.request
import urllib.parse

# Avval login qilamiz
login_url = "http://127.0.0.1:8080/login"
login_data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()

print("=" * 60)
print("1. LOGIN TEST")
print("=" * 60)

try:
    req = urllib.request.Request(login_url, data=login_data, method="POST")
    
    # Redirect ni kuzatmaslik
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    
    opener = urllib.request.build_opener(NoRedirect)
    
    try:
        response = opener.open(req)
    except urllib.error.HTTPError as e:
        if e.code == 303:
            print(f"✅ LOGIN OK! Redirect: {e.code}")
            cookie = e.headers.get('Set-Cookie')
            print(f"✅ Cookie: {cookie[:100]}...")
            
            # Cookie dan session_token ni olish
            session_token = cookie.split(';')[0].split('=')[1]
            print(f"✅ Session token: {session_token[:50]}...")
            
            # Endi home page ga so'rov yuboramiz
            print("\n" + "=" * 60)
            print("2. HOME PAGE TEST (with cookie)")
            print("=" * 60)
            
            home_url = "http://127.0.0.1:8080/"
            home_req = urllib.request.Request(home_url)
            home_req.add_header('Cookie', f'session_token={session_token}')
            
            try:
                home_response = urllib.request.urlopen(home_req)
                print(f"✅ Status: {home_response.status}")
                print(f"✅ HOME PAGE ISHLADI!")
                content = home_response.read().decode()[:500]
                print(f"✅ Content preview: {content}")
            except urllib.error.HTTPError as he:
                print(f"❌ HTTP Error: {he.code}")
                print(f"❌ Response: {he.read().decode()[:1000]}")
        else:
            print(f"❌ HTTP Error: {e.code}")
            print(f"❌ Response: {e.read().decode()[:500]}")
            
except Exception as e:
    print(f"❌ Xato: {e}")
    import traceback
    traceback.print_exc()
