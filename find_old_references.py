# find_old_references.py
import os
import re

# Files to check
files_to_check = [
    'app.py',
    'modules/auth.py',
    'modules/reporting.py',
    'modules/matching.py',
    'modules/admin.py',
    'modules/ai_processing.py',
    'modules/ai_processing_light.py',
    'modules/matching_simple.py',
    'test_routes.py',
    'debug_app.py',
    'find_all_issues.py',
    'create_sample_notifications.py',
]

# Patterns to search for (more specific to avoid false positives)
patterns = [
    # User model patterns
    r'user\.username\b',
    r'\.username\b(?!=)',  # .username but not .username=
    r'User\.username\b',
    r'\busername\b(?=\s*=)',  # username = (in assignments)
    r"request\.form\['username'\]",
    r'current_user\.username\b',
    
    # Email patterns
    r'user\.email\b',
    r'\.email\b(?!=)',
    r'\bemail\b(?=\s*=)',
    r"request\.form\['email'\]",
    
    # Item patterns
    r'item\.title\b',
    r'\.title\b(?!=)',
    r'\btitle\b(?=\s*=)',
    r"request\.form\['title'\]",
    
    r'item\.description\b',
    r'\.description\b(?!=)',
    r'\bdescription\b(?=\s*=)',
    r"request\.form\['description'\]",
    
    r'item\.status\b',
    r'\.status\b(?!=)',
    r'\bstatus\b(?=\s*=)',
    r"request\.form\['status'\]",
    
    r'item\.type\b',
    r'\.type\b(?!=)',
    r'\btype\b(?=\s*=)',
    
    r'item\.location\b',
    r'\.location\b(?!=)',
    r'\blocation\b(?=\s*=)',
    
    r'item\.category\b',
    r'\.category\b(?!=)',
    r'\bcategory\b(?=\s*=)',
    
    # Notification patterns
    r'notification\.message\b',
    r'\.message\b(?!=)',
    r'\bmessage\b(?=\s*=)',
    
    r'notification\.is_seen\b',
    r'\.is_seen\b(?!=)',
    r'\bis_seen\b(?=\s*=)',
    
    # General id patterns (be careful with this)
    # r'\bid\b(?=\s*=)',  # id = assignments
    # r'\.id\b(?!=)',     # .id references
]

print("Searching for old column references...")
print("=" * 60)

for file in files_to_check:
    if os.path.exists(file):
        try:
            # Try reading with UTF-8, fallback to latin-1 if needed
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file, 'r', encoding='latin-1') as f:
                    content = f.read()
            
            lines = content.split('\n')
            
            matches_found = []
            for i, line in enumerate(lines, 1):
                line_has_match = False
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Clean the line for display
                        clean_line = line.strip().replace('\t', ' ').replace('    ', ' ')
                        if len(clean_line) > 100:
                            clean_line = clean_line[:100] + "..."
                        matches_found.append(f"  Line {i}: {clean_line}")
                        line_has_match = True
                        break
            
            if matches_found:
                print(f"\n📁 {file}:")
                for match in matches_found[:15]:  # Show first 15 matches
                    print(match)
                if len(matches_found) > 15:
                    print(f"  ... and {len(matches_found) - 15} more")
        except Exception as e:
            print(f"\n⚠️ Error reading {file}: {e}")

print("\n" + "=" * 60)
print("✅ Search complete!")
print("\nNext steps:")
print("1. Update these references with new column names")
print("2. Example: user.username → user.user_username")
print("3. Example: item.title → item.item_title")