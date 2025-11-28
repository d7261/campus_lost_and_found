import os

def find_auth_references():
    """Find all files that still have auth. references"""
    template_files = []
    
    # Find all template files
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                template_files.append(os.path.join(root, file))
    
    print("🔍 Searching for auth. references in templates...")
    found_issues = False
    
    for file_path in template_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'auth.' in content:
                    found_issues = True
                    print(f"❌ Found auth. references in: {file_path}")
                    # Show the problematic lines
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'auth.' in line:
                            print(f"   Line {i}: {line.strip()}")
        except Exception as e:
            print(f"⚠️  Could not read {file_path}: {e}")
    
    if not found_issues:
        print("✅ No auth. references found in templates!")
    else:
        print("\n💡 Replace all 'auth.' with nothing (e.g., 'auth.login' → 'login')")

if __name__ == '__main__':
    find_auth_references()