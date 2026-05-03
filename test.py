import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("URL:", repr(url))
print("KEY前20字符:", repr(key[:20]) if key else None)

client = create_client(url, key)
result = client.table("inventory_items").select("*").limit(1).execute()
print("结果:", result)