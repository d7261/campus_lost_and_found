from app import app, db
from models import Item
import os

def check_image_storage():
    with app.app_context():
        print("🔍 Checking Image Storage Status...")
        
        # Check upload directory
        upload_dir = 'static/uploads'
        if os.path.exists(upload_dir):
            image_files = os.listdir(upload_dir)
            print(f"✅ Upload directory exists: {upload_dir}")
            print(f"📁 Image files found: {len(image_files)}")
            for img in image_files[:5]:  # Show first 5 files
                print(f"   - {img}")
        else:
            print(f"❌ Upload directory missing: {upload_dir}")
        
        # Check database records
        items_with_images = Item.query.filter(Item.image_path.isnot(None)).all()
        print(f"📊 Database items with image_path: {len(items_with_images)}")
        
        for item in items_with_images[:3]:  # Show first 3 items
            image_path = f"static/uploads/{item.image_path}"
            file_exists = os.path.exists(image_path)
            status = "✅" if file_exists else "❌"
            print(f"   {status} Item {item.id}: {item.title} -> {item.image_path} (File exists: {file_exists})")
        
        # Check total items
        total_items = Item.query.count()
        print(f"📦 Total items in database: {total_items}")

if __name__ == "__main__":
    check_image_storage()