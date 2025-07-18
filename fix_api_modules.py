#!/usr/bin/env python3
"""
Script to fix Canvas API module instantiation issues.
Converts direct API() instantiation to lazy loading pattern.
"""

import os
import re
import glob

def fix_api_file(filepath):
    """Fix a single API file by converting direct instantiation to lazy loading."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find the pattern: variable_name = SomeAPI()
    pattern = r'^(\w+) = (\w+API)\(\)$'
    matches = re.findall(pattern, content, re.MULTILINE)
    
    if not matches:
        return False
    
    # For each match, replace with lazy loading pattern
    for var_name, class_name in matches:
        old_line = f"{var_name} = {class_name}()"
        
        # Create the replacement
        get_function = f"""def get_{var_name}():
    from ..base import access_token, url
    return {class_name}(access_token, url)

class _Lazy{class_name}:
    def __getattr__(self, name):
        return getattr(get_{var_name}(), name)

{var_name} = _Lazy{class_name}()"""
        
        # Replace the old line with new lazy loading pattern
        content = content.replace(
            f"# Convenience instance using environment variables\n{old_line}",
            f"# Lazy-loaded convenience instance\n{get_function}"
        )
        
        # Handle case where there's no comment
        if old_line in content:
            content = content.replace(
                old_line,
                f"# Lazy-loaded convenience instance\n{get_function}"
            )
    
    # Write the fixed content back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed: {filepath}")
    return True

def main():
    """Fix all Canvas API files."""
    # Find all Python files in canvasAPI directory
    api_files = glob.glob("/Users/hamid/projects/CanvasMCP/src/canvasAPI/**/*.py", recursive=True)
    
    fixed_count = 0
    for filepath in api_files:
        if fix_api_file(filepath):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files total.")

if __name__ == "__main__":
    main()