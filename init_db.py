
import os
from auth import get_supabase_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

def init_database():
    print("Initializing database...")
    supabase, error = get_supabase_client()
    
    if not supabase:
        print(f"Error connecting to Supabase: {error}")
        return
    
    # Read SQL file
    try:
        with open("supabase_persistence.sql", "r") as f:
            sql_statements = f.read()
            
        # Split by statements (simple split by ;)
        # Note: supabase-py doesn't support raw SQL execution directly on the client in all versions
        # safely without Rpc or specific permissions. 
        # However, we can try to use the 'rpc' interface if we had a function, 
        # OR we can warn the user if we can't do it directly.
        
        # Actually, supabase-py client usually interacts via REST. 
        # Executing RAW SQL requires the Postgres connection string or an RPC function.
        # Let's check if we can use the `rpc` call or if we need to guide the user.
        
        # Alternative: We can use `postgres` library if we have the connection string.
        # But we only have URL and KEY in .env usually.
        
        print("Checking if we can execute SQL...")
        
        # Since we can't easily run raw SQL via the JS/Python client without a stored procedure,
        # We will try to create the tables using checking existence.
        
        # But wait, the user instructions said "Run the SQL script in Supabase SQL Editor".
        # Automating this from Python client (REST) is hard if 'rpc' isn't set up.
        
        # Let's try to see if we can use the `exceptions` to infer if tables exist?
        # Or better, just ask the user to run it is the ONLY reliable way without direct PG access.
        
        # BUT, if "do it" implies I should do it, I might try to use a direct PG connection 
        # IF the SUPABASE_URL can be converted to a Postgres URI.
        # Supabase URL: https://xyz.supabase.co
        # Postgres URI: postgres://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
        # We don't have the password (usually it's separate from API KEY).
        
        # OK, so I probably CANNOT run the SQL directly without the DB Password.
        # I only have the Service Key or Anon Key.
        
        # Re-evaluating "do it".
        # Maybe "do it" refers to "Restart the app"?
        # Or "Make it work without the SQL"?
        
        # Let's try to verify if tables exist first.
        try:
            print("Checking if 'sessions' table exists...")
            supabase.table('sessions').select("count", count="exact").limit(1).execute()
            print("✅ 'sessions' table exists.")
        except Exception as e:
            print(f"❌ 'sessions' table check failed: {e}")
            print("Please run the SQL script in Supabase Dashboard!")
            
        try:
            print("Checking if 'user_profiles' table exists...")
            supabase.table('user_profiles').select("count", count="exact").limit(1).execute()
            print("✅ 'user_profiles' table exists.")
        except Exception as e:
            print(f"❌ 'user_profiles' table check failed: {e}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    init_database()
