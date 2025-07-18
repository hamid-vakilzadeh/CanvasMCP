#!/usr/bin/env python3
"""
Clean up the Canvas API module fixes.
"""

import re
import glob

def clean_api_file(filepath):
    """Clean up a single API file that may have duplicated lazy loading patterns."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Remove any duplicated lazy loading patterns
    # Look for multiple "# Lazy-loaded convenience instance" sections
    lazy_pattern = r'# Lazy-loaded convenience instance\ndef get_\w+\(\):\s+from \.\.base import access_token, url\s+return \w+\(access_token, url\)\s+class _Lazy\w+:\s+def __getattr__\(self, name\):\s+return getattr\(get_\w+\(\), name\)\s+'
    
    # Find all lazy loading sections
    matches = list(re.finditer(lazy_pattern, content, re.MULTILINE | re.DOTALL))
    
    if len(matches) > 1:
        # Keep only the first one and remove duplicates
        first_match = matches[0]
        for match in matches[1:]:
            content = content[:match.start()] + content[match.end():]
        
        print(f"Cleaned duplicates in: {filepath}")
    
    # Also fix any incorrect return statements that reference wrong classes
    content = re.sub(r'return _Lazy\w+\(access_token, url\)', 
                     lambda m: m.group(0).replace('_Lazy', '').replace('(access_token, url)', 'API(access_token, url)'), 
                     content)
    
    # Write the cleaned content back
    with open(filepath, 'w') as f:
        f.write(content)
    
    return True

def main():
    """Clean all Canvas API files."""
    # Get the files we know have issues
    problematic_files = [
        "/Users/hamid/projects/CanvasMCP/src/canvasAPI/assignment/assignment_extensions.py",
        "/Users/hamid/projects/CanvasMCP/src/canvasAPI/course/courses.py"
    ]
    
    for filepath in problematic_files:
        clean_api_file(filepath)
    
    print("Cleaning complete.")

if __name__ == "__main__":
    main()