from app import app

def check_notification_routes():
    """Check if all notification routes are defined"""
    required_routes = [
        'notifications',
        'mark_notification_seen', 
        'mark_all_notifications_seen'
    ]
    
    print("🔍 Checking notification routes...")
    
    available_routes = [rule.endpoint for rule in app.url_map.iter_rules()]
    
    missing_routes = []
    for route in required_routes:
        if route in available_routes:
            print(f"✅ {route}")
        else:
            missing_routes.append(route)
            print(f"❌ {route} - MISSING")
    
    if missing_routes:
        print(f"\n🚨 Missing {len(missing_routes)} routes:")
        for route in missing_routes:
            print(f"   - {route}")
    else:
        print(f"\n🎉 All notification routes are available!")

if __name__ == '__main__':
    check_notification_routes()