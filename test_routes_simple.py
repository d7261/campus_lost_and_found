import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

def test_routes():
    try:
        # Import the app
        from app import app
        
        print("✅ App imported successfully!")
        print(f"📊 Found {len(app.url_map._rules)} routes")
        
        # List all routes
        print("\n🌐 Available routes:")
        for rule in app.url_map._rules:
            print(f"  {rule.rule} -> {rule.endpoint}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    test_routes()