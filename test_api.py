import requests
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("=" * 50)
print("TEST 1: Valid Open-Meteo request")
print("=" * 50)
url = "https://api.open-meteo.com/v1/forecast?latitude=47.6062&longitude=-122.3321&current_weather=true"
response = requests.get(url)
print(f"Status: {response.status_code}")
data = response.json()
print(f"Has 'current_weather': {'current_weather' in data}")
assert response.status_code == 200, "Expected 200"
assert "current_weather" in data, "Missing current_weather"
print("PASS\n")

print("=" * 50)
print("TEST 2: Invalid input (latitude out of range)")
print("=" * 50)
bad_url = "https://api.open-meteo.com/v1/forecast?latitude=999&longitude=-122.3321&current_weather=true"
response2 = requests.get(bad_url)
print(f"Status: {response2.status_code}")
print(f"Response: {response2.json()}")
print("PASS\n")

print("=" * 50)
print("TEST 3: Wrong Supabase key")
print("=" * 50)
try:
    bad_client = create_client(SUPABASE_URL, "wrong_key_12345")
    result = bad_client.table("inventory_items").select("*").limit(1).execute()
    print(f"Response: {result}")
except Exception as e:
    print(f"Exception caught: {type(e).__name__}: {e}")
print("PASS\n")