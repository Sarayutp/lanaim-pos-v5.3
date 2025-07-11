#!/usr/bin/env python3
"""
Script to fix SQLAlchemy legacy warnings by replacing .query.get() with db.session.get()
Phase 1 - Fix all legacy SQLAlchemy usage
"""

import os
import re

def fix_sqlalchemy_file(file_path):
    """Fix SQLAlchemy legacy warnings in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count replacements
        original_content = content
        
        # Pattern to match db.session.get(Model, id) and replace with db.session.get(Model, id)
        # This handles most common patterns
        patterns_and_replacements = [
            # db.session.get(Menu, id) -> db.session.get(Menu, id)
            (r'Menu\.query\.get\(([^)]+)\)', r'db.session.get(Menu, \1)'),
            # db.session.get(DeliveryZone, id) -> db.session.get(DeliveryZone, id)
            (r'DeliveryZone\.query\.get\(([^)]+)\)', r'db.session.get(DeliveryZone, \1)'),
            # db.session.get(Order, id) -> db.session.get(Order, id)
            (r'Order\.query\.get\(([^)]+)\)', r'db.session.get(Order, \1)'),
            # db.session.get(MenuOptionItem, id) -> db.session.get(MenuOptionItem, id)
            (r'MenuOptionItem\.query\.get\(([^)]+)\)', r'db.session.get(MenuOptionItem, \1)'),
            # db.session.get(Ingredient, id) -> db.session.get(Ingredient, id)
            (r'Ingredient\.query\.get\(([^)]+)\)', r'db.session.get(Ingredient, \1)'),
            # db.session.get(User, id) -> db.session.get(User, id)
            (r'User\.query\.get\(([^)]+)\)', r'db.session.get(User, \1)'),
            # Generic pattern for any db.session.get(Model, id)
            (r'([A-Z][a-zA-Z]*)\.query\.get\(([^)]+)\)', r'db.session.get(\1, \2)'),
        ]
        
        replacement_count = 0
        for pattern, replacement in patterns_and_replacements:
            new_content, count = re.subn(pattern, replacement, content)
            content = new_content
            replacement_count += count
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed {replacement_count} SQLAlchemy warnings in {file_path}")
            return replacement_count
        else:
            return 0
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return 0

def main():
    """Main function to fix all Python files in the project"""
    
    # Base directory
    base_dir = "/Users/sarayutp/Library/CloudStorage/GoogleDrive-brunofernan17042021@gmail.com/My Drive/01_Learning/100_Project/03_LanAim/lan-im-pos_v5.3"
    
    total_fixes = 0
    files_processed = 0
    
    # Walk through all Python files
    for root, dirs, files in os.walk(base_dir):
        # Skip certain directories
        skip_dirs = {'__pycache__', 'venv', 'env', '.git', 'instance'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                files_processed += 1
                fixes = fix_sqlalchemy_file(file_path)
                total_fixes += fixes
    
    print(f"\\n📊 Summary:")
    print(f"Files processed: {files_processed}")
    print(f"Total fixes applied: {total_fixes}")
    print(f"✅ SQLAlchemy legacy warnings fix completed!")

if __name__ == "__main__":
    main()
