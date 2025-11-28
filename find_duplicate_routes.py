from app import app

def find_duplicate_routes():
    routes = {}
    duplicates = []
    
    print("🔍 Checking for duplicate routes...")
    
    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        if endpoint in routes:
            duplicates.append((endpoint, routes[endpoint], str(rule)))
        routes[endpoint] = str(rule)
    
    if duplicates:
        print("❌ Found duplicate routes:")
        for endpoint, old_route, new_route in duplicates:
            print(f"   Endpoint: {endpoint}")
            print(f"   First route: {old_route}")
            print(f"   Second route: {new_route}")
            print()
    else:
        print("✅ No duplicate routes found!")
    
    print(f"📊 Total routes: {len(routes)}")

if __name__ == '__main__':
    find_duplicate_routes()