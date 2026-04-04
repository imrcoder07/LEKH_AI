import os
from dotenv import load_dotenv
from supabase import create_client, Client

def test_connection():
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("[-] Error: SUPABASE_URL or SUPABASE_KEY missing from .env")
        return
        
    print(f"[*] Trying to connect to Supabase project at {url}...")
    
    try:
        supabase: Client = create_client(url, key)
        # Attempt to read from the secure table to verify connectivity (should return empty array if no records)
        response = supabase.table("land_records").select("id").limit(1).execute()
        print("[+] Success! Successfully connected and authenticated with Supabase.")
        print("[+] RLS bypassed successfully using service_role key.")
        print(f"    Table test read response: {response.data}")
    except Exception as e:
        print(f"[-] Connection or Authentication failed: {e}")

if __name__ == "__main__":
    test_connection()
