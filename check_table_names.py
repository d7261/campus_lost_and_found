from app import app, db

def check_table_names():
    with app.app_context():
        print("🔍 Checking actual table names...")
        
        # Get all table names from the database
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print("📊 Tables in database:")
        for table in tables:
            print(f"   - {table}")
            
        # Check columns for each table
        for table in tables:
            print(f"\n🔍 Columns in '{table}':")
            columns = inspector.get_columns(table)
            for column in columns:
                print(f"   - {column['name']} ({column['type']})")

if __name__ == '__main__':
    check_table_names()
    