from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

supabase = create_client(url, key)

print("✓ Supabase connected!")
print("\n📊 Creating missing 3 tables...\n")

# SQL to create missing tables
sql_commands = {
    'appointments': """CREATE TABLE IF NOT EXISTS appointments (
      id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
      user_id TEXT NOT NULL REFERENCES users(email),
      doctor_id BIGINT NOT NULL REFERENCES doctors(id),
      appointment_time TEXT NOT NULL,
      type TEXT NOT NULL,
      status TEXT DEFAULT 'Pending',
      notes TEXT,
      created_at TEXT NOT NULL
    );""",
    
    'baby_tracker': """CREATE TABLE IF NOT EXISTS baby_tracker (
      id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
      user_id TEXT NOT NULL REFERENCES users(email),
      activity_type TEXT NOT NULL,
      start_time TEXT NOT NULL,
      end_time TEXT,
      notes TEXT,
      created_at TEXT NOT NULL
    );""",
    
    'reminders': """CREATE TABLE IF NOT EXISTS reminders (
      id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
      user_id TEXT NOT NULL REFERENCES users(email),
      message TEXT NOT NULL,
      remind_time TEXT NOT NULL,
      created_at TEXT NOT NULL
    );"""
}

print("⚠️  NOTE: You need to run the SQL manually in Supabase SQL Editor.")
print("\n📝 Here's what to do:")
print("1. Go to https://app.supabase.com")
print("2. Click 'SQL Editor' (left sidebar)")
print("3. Click 'New Query'")
print("4. Copy and paste the SQL below")
print("5. Click 'Run'")
print("\n" + "="*70 + "\n")

# Print all SQL
all_sql = "\n\n".join(sql_commands.values())
print(all_sql)

print("\n" + "="*70)
print("\nAfter running the SQL, verify with:")
print("python verify_tables.py")
