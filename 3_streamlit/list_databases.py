#!/usr/bin/env python3
"""
List all databases on the PostgreSQL server
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("=" * 60)
print("📋 LISTANDO DATABASES NO SERVIDOR")
print("=" * 60)
print()

try:
    # Connect to 'postgres' database (always exists)
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database="postgres",  # Default database
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
    
    databases = cursor.fetchall()
    
    print("✅ Databases disponíveis:")
    print()
    for db in databases:
        print(f"   • {db[0]}")
    
    cursor.close()
    conn.close()
    
    print()
    print("=" * 60)
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    exit(1)
