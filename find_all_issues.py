import os
import re

def find_all_url_for_issues():
    """Find all url_for issues in template files"""
    template_files = []
    
    # Find all template files
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                template_files.append(os.path.join(root, file))
    
    print("🔍 Searching for url_for issues in templates...")
    
    url_for_pattern = r"url_for\('([^']+)'\)"
    issues_found = False
    
    for file_path in template_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            matches = re.findall(url_for_pattern, content)
            if matches:
                print(f"\n📄 {file_path}:")
                for match in matches:
                    if 'auth.' in match or 'reporting.' in match:
                        issues_found = True
                        print(f"   ❌ Found: url_for('{match}')")
                        # Suggest correction
                        corrected = match.replace('auth.', '').replace('reporting.', '')
                        print(f"   💡 Should be: url_for('{corrected}')")
                    else:
                        print(f"   ✅ OK: url_for('{match}')")
                        
        except Exception as e:
            print(f"⚠️  Could not read {file_path}: {e}")
    
    if not issues_found:
        print("\n🎉 No url_for issues found!")
    else:
        print("\n💡 Please fix the issues above by removing 'auth.' and 'reporting.' prefixes")

if __name__ == '__main__':
    find_all_url_for_issues()