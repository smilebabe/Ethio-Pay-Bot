#!/usr/bin/env python3
"""
Fix f-string formatting errors in bot.py
"""
import re

def fix_fstrings(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # Fix the specific error on line 1930
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Fix f-string formatting issues
        if ':.0f}' in line:
            # Replace :.0f with :.2f
            lines[i] = line.replace(':.0f}', ':.2f}')
        if ':.0f ' in line:
            lines[i] = line.replace(':.0f ', ':.2f ')
    
    # Join back
    fixed_content = '\n'.join(lines)
    
    with open(filename, 'w') as f:
        f.write(fixed_content)
    
    print("✅ Fixed f-string formatting")

if __name__ == "__main__":
    fix_fstrings("bot.py")
