import requests

url = "http://10.243.49.144:8080/api/agent/location"
data = {
    "latitude": 41.311081,
    "longitude": 69.240562,
    "accuracy": 10,
    "battery": 100,
    "token": "test123"
}

try:
    response = requests.post(url, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
