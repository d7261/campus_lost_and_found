# reset_db.py
import os
import shutil
from app import app
from models import db, User, Item, Notification, ImageEmbedding, Match

def reset_database():
    with app.app_context():
        # 1. Drop all data from tables
        print("🗑️  Deleting all database records...")
        db.session.query(Match).delete()
        db.session.query(ImageEmbedding).delete()
        db.session.query(Notification).delete()
        db.session.query(Item).delete()
        db.session.query(User).delete()
        
        db.session.commit()
        print("✅ Database cleared.")

        # 2. Re-create Admin User
        print("👤 Re-creating Admin user...")
        admin = User(
            user_username='admin',
            user_email='admin@campus.edu',
            user_role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created (admin / admin123)")

        # 3. Clean Uploads Folder
        upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')
        print(f"🧹 Cleaning upload folder: {upload_folder}")
        
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
        else:
            os.makedirs(upload_folder)
            
        print("✅ Uploads folder cleaned.")
        print("🚀 System ready for new test data!")

if __name__ == "__main__":
    reset_database()