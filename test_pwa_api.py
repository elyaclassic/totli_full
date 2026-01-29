import requests

# Test Agent Login
print("=" * 80)
print("TESTING AGENT LOGIN API")
print("=" * 80)

url = "http://10.243.49.144:8080/api/agent/login"
data = {
    "username": "+998901111111",
    "password": "test"
}

response = requests.post(url, data=data)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

if response.json().get("success"):
    token = response.json().get("token")
    user = response.json().get("user")
    
    print("\n" + "=" * 80)
    print("LOGIN SUCCESSFUL!")
    print("=" * 80)
    print(f"User ID: {user['id']}")
    print(f"Name: {user['full_name']}")
    print(f"Token: {token[:50]}...")
    
    # Test Location API
    print("\n" + "=" * 80)
    print("TESTING LOCATION API")
    print("=" * 80)
    
    location_url = "http://10.243.49.144:8080/api/agent/location"
    location_data = {
        "latitude": 41.311081,
        "longitude": 69.240562,
        "accuracy": 10,
        "battery": 100,
        "token": token
    }
    
    location_response = requests.post(location_url, data=location_data)
    print(f"Status Code: {location_response.status_code}")
    print(f"Response: {location_response.json()}")
    
    if location_response.json().get("success"):
        print("\n✅ LOCATION SAVED SUCCESSFULLY!")
    else:
        print("\n❌ LOCATION SAVE FAILED!")
        print(f"Error: {location_response.json().get('error')}")
else:
    print("\n❌ LOGIN FAILED!")
    print(f"Error: {response.json().get('error')}")
