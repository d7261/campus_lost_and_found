from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("Starting migration...")
        
        # Add columns to users table
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS user_is_suspended BOOLEAN DEFAULT FALSE"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS user_suspension_reason VARCHAR(255)"))
            db.session.commit()
            print("✅ Columns added to users table (or already existed)")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding columns: {e}")
        
        # Create new tables
        try:
            db.create_all()
            print("✅ New tables created (Flag, Category, CampusLocation)")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
        
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
