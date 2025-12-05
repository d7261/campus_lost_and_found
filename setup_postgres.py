#!/usr/bin/env python3
"""
Setup PostgreSQL for Campus Lost & Found
"""
import os
import sys
import subprocess
from urllib.parse import urlparse

def check_postgres_installation():
    """Check if PostgreSQL is installed and running"""
    try:
        result = subprocess.run(['psql', '--version'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ PostgreSQL is installed:", result.stdout.strip())
            return True
        else:
            print("❌ PostgreSQL is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("❌ PostgreSQL is not installed or not in PATH")
        return False

def create_database():
    """Create PostgreSQL database if it doesn't exist"""
    print("\n📦 Setting up PostgreSQL database...")
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': '5432',
        'database': 'campus_lost_found',
        'user': 'postgres',
        'password': 'password'  # Change this!
    }
    
    try:
        # Try to connect to check if database exists
        import psycopg2
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database='postgres'  # Connect to default database first
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", 
                      (db_config['database'],))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database '{db_config['database']}'...")
            cursor.execute(f"CREATE DATABASE {db_config['database']}")
            print(f"✅ Database created successfully")
        else:
            print(f"✅ Database '{db_config['database']}' already exists")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def test_connection():
    """Test PostgreSQL connection"""
    print("\n🔗 Testing PostgreSQL connection...")
    
    try:
        # Import here to avoid early failure
        from app import create_app
        from flask import Flask
        
        app = create_app()
        
        # Override config for test
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost:5432/campus_lost_found'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        with app.app_context():
            from models import db
            db.engine.connect()
            print("✅ PostgreSQL connection successful!")
            
            # Try to create tables
            db.create_all()
            print("✅ Tables created successfully")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def migrate_data_from_sqlite():
    """Optional: Migrate data from SQLite to PostgreSQL"""
    print("\n🔄 Data migration (optional)...")
    
    response = input("Do you want to migrate data from SQLite? (y/N): ")
    if response.lower() != 'y':
        print("Skipping data migration")
        return
    
    # Check if SQLite database exists
    if not os.path.exists('instance/database.db'):
        print("❌ SQLite database not found at 'instance/database.db'")
        return
    
    print("Creating migration script...")
    
    migration_script = """
# Run this script to migrate data
python -c "
import sqlite3
import psycopg2
from datetime import datetime

print('Starting migration...')

# Connect to SQLite
sqlite_conn = sqlite3.connect('instance/database.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

# Connect to PostgreSQL
pg_conn = psycopg2.connect('postgresql://postgres:password@localhost:5432/campus_lost_found')
pg_cur = pg_conn.cursor()

# Get all tables
sqlite_cur.execute(\"SELECT name FROM sqlite_master WHERE type='table';\")
tables = [row[0] for row in sqlite_cur.fetchall()]

for table in tables:
    print(f'Migrating {{table}}...')
    
    # Get data
    sqlite_cur.execute(f'SELECT * FROM {{table}}')
    rows = sqlite_cur.fetchall()
    
    if rows:
        # Get column names
        columns = [description[0] for description in sqlite_cur.description]
        
        # Clear existing data in PostgreSQL
        pg_cur.execute(f'TRUNCATE TABLE {{table}} CASCADE')
        
        # Insert data
        for row in rows:
            values = [row[col] for col in columns]
            placeholders = ', '.join(['%s'] * len(values))
            columns_str = ', '.join(columns)
            query = f'INSERT INTO {{table}} ({{columns_str}}) VALUES ({{placeholders}})'
            pg_cur.execute(query, values)
    
    pg_conn.commit()

print('Migration completed!')

sqlite_conn.close()
pg_cur.close()
pg_conn.close()
"
"""
    
    with open('migrate_data.py', 'w') as f:
        f.write(migration_script)
    
    print("✅ Migration script created as 'migrate_data.py'")
    print("Run: python migrate_data.py")

def main():
    print("=" * 50)
    print("PostgreSQL Setup for Campus Lost & Found")
    print("=" * 50)
    
    # Check PostgreSQL installation
    if not check_postgres_installation():
        print("\n📥 Please install PostgreSQL first:")
        print("  macOS: brew install postgresql")
        print("  Ubuntu: sudo apt install postgresql postgresql-contrib")
        print("  Windows: Download from https://www.postgresql.org/download/")
        return
    
    # Create database
    if not create_database():
        return
    
    # Test connection
    if not test_connection():
        return
    
    # Offer data migration
    migrate_data_from_sqlite()
    
    print("\n" + "=" * 50)
    print("✅ Setup completed!")
    print("\nNext steps:")
    print("1. Update config.py with PostgreSQL URL")
    print("2. Run your app: python app.py")
    print("3. Your app will now use PostgreSQL!")
    print("=" * 50)

if __name__ == '__main__':
    main()