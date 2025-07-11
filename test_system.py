#!/usr/bin/env python3
"""
Database Operations Test Script
Phase 1 - Test all CRUD operations and API endpoints

This script tests:
1. Database connectivity
2. Model CRUD operations
3. API endpoints functionality
4. Data integrity
"""

import requests
import json
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append('/Users/sarayutp/Library/CloudStorage/GoogleDrive-brunofernan17042021@gmail.com/My Drive/01_Learning/100_Project/03_LanAim/lan-im-pos_v5.3')

def test_api_endpoint(url, method='GET', data=None, headers=None, expected_status=200):
    """Generic API endpoint tester"""
    try:
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        
        print(f"{'✅' if response.status_code == expected_status else '❌'} {method} {url} - Status: {response.status_code}")
        
        if response.status_code != expected_status:
            print(f"   Expected: {expected_status}, Got: {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:200]}...")
        
        return response
        
    except requests.exceptions.ConnectionError:
        print(f"❌ {method} {url} - Connection Error (Server not running?)")
        return None
    except Exception as e:
        print(f"❌ {method} {url} - Error: {e}")
        return None

def test_database_operations():
    """Test direct database operations"""
    print("\\n🔍 Testing Database Operations...")
    
    try:
        # Import after adding to path
        from app import create_app
        from models import db, Menu, Ingredient, DeliveryZone, User
        
        # Create app context
        app = create_app('testing')
        
        with app.app_context():
            print("✅ Database connection successful")
            
            # Test basic queries
            try:
                menu_count = Menu.query.count()
                ingredient_count = Ingredient.query.count()
                zone_count = DeliveryZone.query.count()
                
                print(f"✅ Menu items: {menu_count}")
                print(f"✅ Ingredients: {ingredient_count}")
                print(f"✅ Delivery zones: {zone_count}")
                
                # Test a simple create operation
                test_menu = Menu(
                    name="Test Menu Item",
                    description="Test description",
                    price=99.99,
                    category="Test Category",
                    is_active=True
                )
                
                db.session.add(test_menu)
                db.session.commit()
                print("✅ Create operation successful")
                
                # Test update operation
                test_menu.price = 129.99
                db.session.commit()
                print("✅ Update operation successful")
                
                # Test delete operation
                db.session.delete(test_menu)
                db.session.commit()
                print("✅ Delete operation successful")
                
            except Exception as e:
                print(f"❌ Database operation failed: {e}")
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

def test_admin_api():
    """Test admin API endpoints"""
    print("\\n🔍 Testing Admin API Endpoints...")
    
    base_url = "http://localhost:5002"
    
    # Note: These tests assume the server is running and admin is logged in
    # In a real scenario, we'd need to handle authentication
    
    endpoints_to_test = [
        # Menu endpoints
        (f"{base_url}/admin/api/menu", "GET", None, 200),
        (f"{base_url}/admin/api/categories", "GET", None, 200),
        
        # Ingredient endpoints  
        (f"{base_url}/admin/api/ingredient", "GET", None, 200),
        (f"{base_url}/admin/api/low-stock", "GET", None, 200),
        
        # Zone endpoints
        (f"{base_url}/admin/api/zone", "GET", None, 200),
    ]
    
    for url, method, data, expected_status in endpoints_to_test:
        test_api_endpoint(url, method, data, expected_status=expected_status)

def test_customer_api():
    """Test customer-facing API endpoints"""
    print("\\n🔍 Testing Customer API Endpoints...")
    
    base_url = "http://localhost:5002"
    
    endpoints_to_test = [
        (f"{base_url}/api/zones", "GET", None, 200),
        (f"{base_url}/api/menu", "GET", None, 200),
        (f"{base_url}/", "GET", None, 200),  # Main page
    ]
    
    for url, method, data, expected_status in endpoints_to_test:
        test_api_endpoint(url, method, data, expected_status=expected_status)

def test_admin_pages():
    """Test admin page accessibility"""
    print("\\n🔍 Testing Admin Pages...")
    
    base_url = "http://localhost:5002"
    
    # Test admin pages (may redirect to login if not authenticated)
    admin_pages = [
        f"{base_url}/admin/login",
        f"{base_url}/admin/dashboard",
        f"{base_url}/admin/menu", 
        f"{base_url}/admin/ingredients",
        f"{base_url}/admin/zones",
        f"{base_url}/admin/analytics",
        f"{base_url}/admin/reports",
        f"{base_url}/admin/profile",
    ]
    
    for url in admin_pages:
        # Accept both 200 (if logged in) and 302 (redirect to login)
        response = test_api_endpoint(url, expected_status=200)
        if response and response.status_code == 302:
            print(f"   ↳ Redirected (not logged in) - Normal behavior")

def create_test_data():
    """Create sample test data for comprehensive testing"""
    print("\\n🔍 Creating Test Data...")
    
    try:
        from app import create_app
        from models import db, Menu, Ingredient, DeliveryZone
        
        app = create_app('testing')
        
        with app.app_context():
            # Create test ingredients
            test_ingredients = [
                {"name": "Test Rice", "unit": "kg", "cost_per_unit": 50, "stock_quantity": 100},
                {"name": "Test Chicken", "unit": "kg", "cost_per_unit": 180, "stock_quantity": 50},
                {"name": "Test Vegetables", "unit": "kg", "cost_per_unit": 30, "stock_quantity": 75},
            ]
            
            for ing_data in test_ingredients:
                # Check if already exists
                existing = Ingredient.query.filter_by(name=ing_data["name"]).first()
                if not existing:
                    ingredient = Ingredient(**ing_data)
                    db.session.add(ingredient)
            
            # Create test menus
            test_menus = [
                {"name": "Test Fried Rice", "price": 45, "category": "Rice Dishes", "description": "Test delicious fried rice"},
                {"name": "Test Chicken Curry", "price": 65, "category": "Curry", "description": "Test spicy chicken curry"},
                {"name": "Test Pad Thai", "price": 55, "category": "Noodles", "description": "Test traditional pad thai"},
            ]
            
            for menu_data in test_menus:
                existing = Menu.query.filter_by(name=menu_data["name"]).first()
                if not existing:
                    menu = Menu(**menu_data, is_active=True)
                    db.session.add(menu)
            
            # Create test delivery zones
            test_zones = [
                {"name": "Test Zone A", "delivery_fee": 15, "description": "Test delivery zone A"},
                {"name": "Test Zone B", "delivery_fee": 25, "description": "Test delivery zone B"},
            ]
            
            for zone_data in test_zones:
                existing = DeliveryZone.query.filter_by(name=zone_data["name"]).first()
                if not existing:
                    zone = DeliveryZone(**zone_data, is_active=True)
                    db.session.add(zone)
            
            db.session.commit()
            print("✅ Test data created successfully")
            
    except Exception as e:
        print(f"❌ Failed to create test data: {e}")

def main():
    """Main test function"""
    print("🚀 LanAim POS v5.3 - Phase 1 Testing")
    print("=" * 50)
    print(f"Test started at: {datetime.now()}")
    
    # Run all tests
    test_database_operations()
    create_test_data()
    test_customer_api()
    test_admin_api() 
    test_admin_pages()
    
    print("\\n" + "=" * 50)
    print("🏁 Testing completed!")
    print(f"Test finished at: {datetime.now()}")
    print("\\nNote: Some API endpoints may require authentication")
    print("      Start the server with: python app.py")

if __name__ == "__main__":
    main()
