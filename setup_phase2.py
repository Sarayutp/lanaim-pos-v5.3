#!/usr/bin/env python3
"""
LanAim POS System v2.4 - Phase 2 Setup Script
Database initialization and sample data creation for Phase 2

This script sets up the database with Phase 2 models and creates
sample data for testing admin functionality.
"""

import os
import sys
from flask import Flask

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import (
    db, create_sample_data, setup_phase2_data,
    create_admin_user, create_sample_ingredients,
    create_sample_bom, create_sample_promotion
)

def setup_phase2_database():
    """Setup Phase 2 database and sample data"""
    
    print("🚀 LanAim POS System v2.4 - Phase 2 Setup")
    print("=" * 50)
    
    # Create Flask app
    app = create_app('development')
    
    with app.app_context():
        print("📊 Creating database tables...")
        
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully!")
        
        print("\n👤 Setting up admin user...")
        # Create admin user
        admin = create_admin_user()
        print(f"✅ Admin user created: {admin.username}")
        
        print("\n📋 Creating Phase 1 sample data...")
        # Create Phase 1 sample data if not exists
        try:
            create_sample_data()
            print("✅ Phase 1 sample data created!")
        except Exception as e:
            print(f"ℹ️  Phase 1 data may already exist: {e}")
        
        print("\n🏪 Setting up Phase 2 data...")
        # Setup Phase 2 specific data
        setup_phase2_data()
        print("✅ Phase 2 sample data created successfully!")
        
        print("\n🎉 Setup completed successfully!")
        print("\n" + "=" * 50)
        print("📝 Quick Start Information:")
        print("=" * 50)
        print("🌐 Admin Panel: http://localhost:5001/admin")
        print("👤 Admin Login:")
        print("   Username: admin")
        print("   Password: admin123")
        print("\n🏠 Main Application: http://localhost:5001")
        print("🍽️  Customer Order: http://localhost:5001/customer/menu")
        print("👨‍🍳 Kitchen Staff: http://localhost:5001/staff/kitchen")
        print("🚚 Delivery Staff: http://localhost:5001/staff/delivery")
        print("\n⚠️  IMPORTANT: Change the admin password in production!")
        print("=" * 50)

def reset_database():
    """Reset database (DANGER: This will delete all data!)"""
    
    response = input("\n⚠️  WARNING: This will delete ALL data! Are you sure? (type 'YES' to confirm): ")
    
    if response == 'YES':
        app = create_app('development')
        with app.app_context():
            print("🗑️  Dropping all tables...")
            db.drop_all()
            print("✅ All tables dropped!")
            
            print("📊 Recreating tables...")
            db.create_all()
            print("✅ Tables recreated!")
            
            print("📋 Setting up fresh data...")
            setup_phase2_database()
    else:
        print("❌ Database reset cancelled.")

def main():
    """Main setup function"""
    
    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        reset_database()
    else:
        setup_phase2_database()

if __name__ == '__main__':
    main()
