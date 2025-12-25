#!/usr/bin/env python3
"""
Script to remove problematic CSS properties that cause warnings in Qt
"""

import re

def fix_css_warnings(file_path):
    """Remove CSS properties that Qt doesn't support"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove problematic CSS properties
    problematic_properties = [
        r'\s*-webkit-font-smoothing:[^;]+;',
        r'\s*-moz-osx-font-smoothing:[^;]+;', 
        r'\s*text-rendering:[^;]+;',
        r'\s*box-shadow:[^;]+;',
        r'\s*transition:[^;]+;',
        r'\s*transform:[^;]+;',
        r'\s*z-index:[^;]+;'
    ]
    
    for pattern in problematic_properties:
        content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    # Clean up empty CSS blocks
    content = re.sub(r'/\*[^*]*\*/\s*\{\s*\}', '', content, flags=re.MULTILINE)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed CSS warnings in {file_path}")

if __name__ == "__main__":
    fix_css_warnings("modern_gui_interface.py")