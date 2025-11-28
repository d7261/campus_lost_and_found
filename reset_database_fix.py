import os
from app import app, db, User

def reset_database():
    print("🔄 Resetting database to apply new schema...")
    
    # Remove existing database
    if os.path.exists('campus.db'):
        os.remove('campus.db')
        print("✅ Removed old database")
    
    # Create new tables with updated schema
    with app.app_context():
        db.create_all()
        print("✅ Created new database with updated schema")
        
        # Create admin user
        admin = User(username='admin', email='admin@campus.edu', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("👑 Admin user created: admin / admin123")
        
        print("🎉 Database reset complete!")
        print("💡 You'll need to register new accounts and report items again")

if __name__ == '__main__':
    reset_database()