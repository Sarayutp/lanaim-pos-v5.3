#!/usr/bin/env python3
"""
Database Schema Migration Script
Adds missing columns to menu_option_groups table
"""

import sqlite3
import os
import sys

def fix_database_schema():
    """Add missing columns to database tables"""
    
    # Database path
    db_path = 'lanaim_pos_phase1.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found!")
        return False
    
    # Backup database first
    backup_path = f"{db_path}.backup"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to {backup_path}")
    except Exception as e:
        print(f"⚠️  Could not create backup: {e}")
        response = input("Continue without backup? (y/N): ")
        if response.lower() != 'y':
            return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking existing schema...")
        
        # Check current columns in menu_option_groups table
        cursor.execute("PRAGMA table_info(menu_option_groups)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        # Add missing columns if they don't exist
        columns_to_add = []
        
        if 'is_multiple' not in columns:
            columns_to_add.append(('is_multiple', 'BOOLEAN DEFAULT 0 NOT NULL'))
            
        if 'is_active' not in columns:
            columns_to_add.append(('is_active', 'BOOLEAN DEFAULT 1 NOT NULL'))
        
        if columns_to_add:
            print(f"📝 Adding missing columns: {[col[0] for col in columns_to_add]}")
            
            for column_name, column_def in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE menu_option_groups ADD COLUMN {column_name} {column_def}")
                    print(f"✅ Added column: {column_name}")
                except sqlite3.Error as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"ℹ️  Column {column_name} already exists")
                    else:
                        print(f"❌ Error adding column {column_name}: {e}")
                        raise
            
            # Update existing records to have sensible defaults
            cursor.execute("""
                UPDATE menu_option_groups 
                SET is_multiple = 0, is_active = 1 
                WHERE is_multiple IS NULL OR is_active IS NULL
            """)
            
            conn.commit()
            print("✅ Database schema updated successfully!")
            
        else:
            print("ℹ️  All required columns already exist")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(menu_option_groups)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"Updated columns: {updated_columns}")
        
        # Test a simple query to make sure everything works
        cursor.execute("SELECT COUNT(*) FROM menu_option_groups")
        count = cursor.fetchone()[0]
        print(f"✅ Table accessible - found {count} option groups")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        
        # Try to restore backup if available
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, db_path)
                print(f"🔄 Database restored from backup")
            except Exception as restore_error:
                print(f"❌ Could not restore backup: {restore_error}")
        
        return False

if __name__ == "__main__":
    print("🛠️  LanAim POS Database Schema Migration")
    print("=" * 50)
    
    success = fix_database_schema()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now start the application.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above.")
        sys.exit(1)