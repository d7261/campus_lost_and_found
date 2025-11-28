import os
from app import app, db

def check_database_status():
    print("🔍 Checking database status...")
    
    # Check if database file exists
    db_files = ['campus.db', 'instance/campus.db']
    db_exists = False
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"✅ Database found: {db_file}")
            db_exists = True
            break
    
    if not db_exists:
        print("❌ No database file found!")
        print("💡 The database will be created when you run the app")
    
    # Try to create tables
    try:
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 Tables created: {tables}")
            
    except Exception as e:
        print(f"❌ Error creating database: {e}")

if __name__ == '__main__':
    check_database_status()