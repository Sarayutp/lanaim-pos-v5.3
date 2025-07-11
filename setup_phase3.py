#!/usr/bin/env python3
"""
LanAim POS System v2.4 - Phase 3 Setup
Database initialization and sample data for Phase 3

This script sets up the Phase 3 database with enhanced analytics models
and creates comprehensive sample data for testing.
"""

import os
import sys
from datetime import datetime, timedelta, time
from decimal import Decimal
import random

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import (
    db, User, DeliveryZone, Menu, MenuOptionGroup, MenuOptionItem,
    Order, OrderItem, OrderItemOption, Feedback, Ingredient, RecipeBOM,
    StockAdjustment, Promotion, DailyReport, HourlyStats, MenuPopularity,
    CustomerSession, get_thai_now, update_daily_report, update_hourly_stats,
    update_menu_popularity
)

def create_sample_data():
    """Create comprehensive sample data for Phase 3 testing"""
    
    print("🚀 Creating Phase 3 sample data...")
    
    # Create admin user if not exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(username='admin', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        print("✅ Created admin user")
    
    # Create staff users
    kitchen_staff = User.query.filter_by(username='kitchen').first()
    if not kitchen_staff:
        kitchen_staff = User(username='kitchen', role='kitchen_staff')
        kitchen_staff.set_password('kitchen123')
        db.session.add(kitchen_staff)
        print("✅ Created kitchen staff user")
    
    delivery_staff = User.query.filter_by(username='delivery').first()
    if not delivery_staff:
        delivery_staff = User(username='delivery', role='delivery_staff')
        delivery_staff.set_password('delivery123')
        db.session.add(delivery_staff)
        print("✅ Created delivery staff user")
    
    # Create delivery zones
    zones_data = [
        {'name': 'โซน A - ชั้น 1', 'description': 'โต๊ะ A1-A10'},
        {'name': 'โซน B - ชั้น 1', 'description': 'โต๊ะ B1-B10'},
        {'name': 'โซน C - ชั้น 2', 'description': 'โต๊ะ C1-C8'},
        {'name': 'บริการส่งนอกร้าน', 'description': 'พื้นที่ส่งภายใน 5 กม.'}
    ]
    
    for zone_data in zones_data:
        zone = DeliveryZone.query.filter_by(name=zone_data['name']).first()
        if not zone:
            zone = DeliveryZone(**zone_data)
            db.session.add(zone)
    
    db.session.commit()
    print("✅ Created delivery zones")
    
    # Create ingredients
    ingredients_data = [
        {'name': 'ข้าวสวย', 'unit': 'กิโลกรัม', 'stock_quantity': 50, 'low_stock_threshold': 10, 'cost_per_unit': 25},
        {'name': 'เนื้อหมู', 'unit': 'กิโลกรัม', 'stock_quantity': 20, 'low_stock_threshold': 5, 'cost_per_unit': 180},
        {'name': 'เนื้อไก่', 'unit': 'กิโลกรัม', 'stock_quantity': 15, 'low_stock_threshold': 3, 'cost_per_unit': 120},
        {'name': 'ไข่ไก่', 'unit': 'ฟอง', 'stock_quantity': 200, 'low_stock_threshold': 30, 'cost_per_unit': 4},
        {'name': 'ผักบุ้งจีน', 'unit': 'กิโลกรัม', 'stock_quantity': 8, 'low_stock_threshold': 2, 'cost_per_unit': 40},
        {'name': 'น้ำมันพืช', 'unit': 'ลิตร', 'stock_quantity': 10, 'low_stock_threshold': 2, 'cost_per_unit': 45},
        {'name': 'ซอสหอยนางรม', 'unit': 'ขวด', 'stock_quantity': 5, 'low_stock_threshold': 1, 'cost_per_unit': 35},
        {'name': 'กุ้งสด', 'unit': 'กิโลกรัม', 'stock_quantity': 3, 'low_stock_threshold': 1, 'cost_per_unit': 250},
        {'name': 'มะเขือเทศ', 'unit': 'กิโลกรัม', 'stock_quantity': 5, 'low_stock_threshold': 1, 'cost_per_unit': 30},
        {'name': 'หอมใหญ่', 'unit': 'กิโลกรัม', 'stock_quantity': 3, 'low_stock_threshold': 1, 'cost_per_unit': 25}
    ]
    
    for ing_data in ingredients_data:
        ingredient = Ingredient.query.filter_by(name=ing_data['name']).first()
        if not ingredient:
            ingredient = Ingredient(**ing_data)
            db.session.add(ingredient)
    
    db.session.commit()
    print("✅ Created ingredients")
    
    # Create menu items with enhanced variety
    menu_items = [
        # Rice dishes
        {'name': 'ข้าวผัดหมู', 'price': 45, 'category': 'ข้าว', 'description': 'ข้าวผัดหมูแบบดั้งเดิม'},
        {'name': 'ข้าวผัดไก่', 'price': 40, 'category': 'ข้าว', 'description': 'ข้าวผัดไก่สไตล์ไทย'},
        {'name': 'ข้าวผัดกุ้ง', 'price': 60, 'category': 'ข้าว', 'description': 'ข้าวผัดกุ้งสด หอมกรุ่น'},
        {'name': 'ข้าวผัดไข่', 'price': 35, 'category': 'ข้าว', 'description': 'ข้าวผัดไข่เจ'},
        {'name': 'ข้าวคลุกกะปิ', 'price': 50, 'category': 'ข้าว', 'description': 'ข้าวคลุกกะปิกับเครื่องเคียง'},
        
        # Stir-fried dishes
        {'name': 'ผัดไทยกุ้งสด', 'price': 65, 'category': 'ผัด', 'description': 'ผัดไทยใส่กุ้งสดตัวใหญ่'},
        {'name': 'ผัดซีอิ๊วหมู', 'price': 45, 'category': 'ผัด', 'description': 'เส้นใหญ่ผัดซีอิ๊วดำใส่หมู'},
        {'name': 'ผัดบุ้งไฟแดง', 'price': 40, 'category': 'ผัด', 'description': 'ผักบุ้งจีนผัดน้ำมันหอย'},
        {'name': 'ราดหน้าหมู', 'price': 50, 'category': 'ผัด', 'description': 'เส้นใหญ่ราดหน้าใส่หมู'},
        
        # Soups
        {'name': 'ต้มยำกุ้ง', 'price': 70, 'category': 'แกง/ต้ม', 'description': 'ต้มยำกุ้งน้ำใสรสจัดจ้าน'},
        {'name': 'แกงเขียวหวานไก่', 'price': 55, 'category': 'แกง/ต้ม', 'description': 'แกงเขียวหวานไก่เนื้อนุ่ม'},
        {'name': 'ต้มข่าไก่', 'price': 50, 'category': 'แกง/ต้ม', 'description': 'ต้มข่าไก่กะทิสด'},
        
        # Salads
        {'name': 'ส้มตำไทย', 'price': 35, 'category': 'ยำ/สลัด', 'description': 'ส้มตำใส่ถั่วฝักยาว มะเขือเทศ'},
        {'name': 'ลาบหมู', 'price': 45, 'category': 'ยำ/สลัด', 'description': 'ลาบหมูสับใส่สมุนไพรไทย'},
        {'name': 'ยำวุ้นเส้น', 'price': 40, 'category': 'ยำ/สลัด', 'description': 'ยำวุ้นเส้นกุ้งสับ'},
        
        # Beverages
        {'name': 'น้ำเปล่า', 'price': 10, 'category': 'เครื่องดื่ม', 'description': 'น้ำดื่มขวด'},
        {'name': 'โค้ก', 'price': 15, 'category': 'เครื่องดื่ม', 'description': 'โคคาโคล่า'},
        {'name': 'ชาไทย', 'price': 25, 'category': 'เครื่องดื่ม', 'description': 'ชาไทยเย็นหวานมัน'},
        {'name': 'กาแฟเย็น', 'price': 30, 'category': 'เครื่องดื่ม', 'description': 'กาแฟโบราณเย็น'},
        {'name': 'น้ำส้มคั้น', 'price': 35, 'category': 'เครื่องดื่ม', 'description': 'น้ำส้มสดคั้นใหม่'}
    ]
    
    for menu_data in menu_items:
        menu = Menu.query.filter_by(name=menu_data['name']).first()
        if not menu:
            menu = Menu(**menu_data)
            db.session.add(menu)
    
    db.session.commit()
    print("✅ Created menu items")
    
    # Create option groups for some menu items
    rice_menu = Menu.query.filter_by(name='ข้าวผัดหมู').first()
    if rice_menu:
        # Spice level option
        spice_group = MenuOptionGroup.query.filter_by(menu_id=rice_menu.id, name='ระดับความเผ็ด').first()
        if not spice_group:
            spice_group = MenuOptionGroup(
                menu_id=rice_menu.id,
                name='ระดับความเผ็ด',
                is_required=False,
                max_selections=1
            )
            db.session.add(spice_group)
            db.session.flush()
            
            spice_options = [
                {'name': 'ไม่เผ็ด', 'additional_price': 0},
                {'name': 'เผ็ดน้อย', 'additional_price': 0},
                {'name': 'เผ็ดปานกลาง', 'additional_price': 0},
                {'name': 'เผ็ดมาก', 'additional_price': 0}
            ]
            
            for opt_data in spice_options:
                option = MenuOptionItem(
                    group_id=spice_group.id,
                    **opt_data
                )
                db.session.add(option)
        
        # Extra items option
        extra_group = MenuOptionGroup.query.filter_by(menu_id=rice_menu.id, name='เพิ่มเติม').first()
        if not extra_group:
            extra_group = MenuOptionGroup(
                menu_id=rice_menu.id,
                name='เพิ่มเติม',
                is_required=False,
                max_selections=3
            )
            db.session.add(extra_group)
            db.session.flush()
            
            extra_options = [
                {'name': 'ไข่ดาว', 'additional_price': 10},
                {'name': 'ไข่เจียว', 'additional_price': 15},
                {'name': 'หมูกรอบ', 'additional_price': 20},
                {'name': 'ผักเพิ่ม', 'additional_price': 5}
            ]
            
            for opt_data in extra_options:
                option = MenuOptionItem(
                    group_id=extra_group.id,
                    **opt_data
                )
                db.session.add(option)
    
    db.session.commit()
    print("✅ Created menu options")
    
    # Create historical orders (last 30 days) for analytics
    create_historical_orders()
    
    print("✅ Phase 3 sample data created successfully!")

def create_historical_orders():
    """Create historical orders for the last 30 days for analytics testing"""
    
    print("📊 Creating historical orders for analytics...")
    
    zones = DeliveryZone.query.all()
    menus = Menu.query.all()
    
    if not zones or not menus:
        print("❌ No zones or menus found. Skipping historical orders.")
        return
    
    # Create orders for the last 30 days
    now = get_thai_now()
    start_date = now - timedelta(days=30)
    
    customer_names = [
        'สมชาย ใจดี', 'สมศรี รักเรียน', 'นิรันดร์ สุขใจ', 'วิไล แสงดี',
        'ประเสริฐ กิจเจริญ', 'สุมาลี ปราณี', 'วีระ เก่งเก้า', 'ปิยะ รักษ์ใจ',
        'อนันต์ เพชรดี', 'สุกัญญา ใจงาม', 'ธนภัทร อยู่ดี', 'รัชดา มั่นคง',
        'จิรายุ ปัญญา', 'นันทนา สงบใจ', 'ภูมิใจ ศิลป์', 'กนกวรรณ รักดี'
    ]
    
    phone_numbers = [
        '081-234-5678', '082-345-6789', '083-456-7890', '084-567-8901',
        '085-678-9012', '086-789-0123', '087-890-1234', '088-901-2345'
    ]
    
    # Define realistic order patterns by hour
    hourly_weights = {
        6: 1, 7: 2, 8: 3, 9: 2, 10: 1,  # Morning
        11: 8, 12: 10, 13: 8, 14: 3,    # Lunch peak
        15: 1, 16: 2, 17: 4, 18: 9,     # Afternoon/Early dinner
        19: 10, 20: 8, 21: 5, 22: 2,    # Dinner peak
        23: 1, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0  # Night/Early morning
    }
    
    total_orders = 0
    
    for day_offset in range(30):
        current_date = start_date + timedelta(days=day_offset)
        
        # Weekend effect (more orders on weekends)
        weekend_multiplier = 1.5 if current_date.weekday() >= 5 else 1.0
        
        # Daily base orders (15-25 per day)
        daily_base_orders = random.randint(15, 25)
        daily_orders = int(daily_base_orders * weekend_multiplier)
        
        for _ in range(daily_orders):
            # Select hour based on realistic patterns
            hour = random.choices(
                list(hourly_weights.keys()),
                weights=list(hourly_weights.values())
            )[0]
            
            # Create realistic timestamp
            order_time = current_date.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Create order
            order = Order(
                customer_name=random.choice(customer_names),
                customer_phone=random.choice(phone_numbers),
                delivery_address_details=f'ที่อยู่ {random.randint(1, 100)} ซอย {random.randint(1, 20)}',
                delivery_zone_id=random.choice(zones).id,
                total_price=0,  # Will be calculated
                payment_method='COD',  # Add required field
                created_at=order_time
            )
            
            # Generate order number
            order.generate_order_number()
            
            # Set random status based on time
            age_hours = (now - order_time).total_seconds() / 3600
            if age_hours > 2:
                # Old orders should be completed
                status_choices = ['delivered', 'completed', 'cancelled']
                weights = [70, 25, 5]  # 70% delivered, 25% completed, 5% cancelled
                order.status = random.choices(status_choices, weights=weights)[0]
                
                if order.status in ['delivered', 'completed']:
                    order.accepted_at = order_time + timedelta(minutes=random.randint(2, 8))
                    order.completed_at = order.accepted_at + timedelta(minutes=random.randint(15, 30))
                    order.payment_status = 'paid'
            elif age_hours > 0.5:
                # Recent orders might be in progress
                order.status = random.choice(['accepted', 'preparing', 'ready'])
                order.accepted_at = order_time + timedelta(minutes=random.randint(2, 8))
            # else: keep as 'pending'
            
            db.session.add(order)
            db.session.flush()
            
            # Add order items (1-4 items per order)
            num_items = random.randint(1, 4)
            selected_menus = random.sample(menus, min(num_items, len(menus)))
            
            total_price = 0
            
            for menu in selected_menus:
                quantity = random.randint(1, 2)
                item_price = float(menu.price) * quantity
                
                order_item = OrderItem(
                    order_id=order.id,
                    menu_id=menu.id,
                    menu_name=menu.name,
                    quantity=quantity,
                    price_per_item=menu.price
                )
                db.session.add(order_item)
                total_price += item_price
            
            order.total_price = total_price
            
            # Add feedback for completed orders (60% chance)
            if order.status in ['delivered', 'completed'] and random.random() < 0.6:
                # More recent orders get better ratings
                if age_hours < 24:
                    rating_weights = [5, 15, 20, 30, 30]  # 1-5 stars, skewed positive for recent
                else:
                    rating_weights = [10, 10, 20, 30, 30]  # More balanced for older
                
                rating = random.choices([1, 2, 3, 4, 5], weights=rating_weights)[0]
                
                comments = {
                    5: ['อร่อยมาก!', 'ประทับใจครับ', 'ดีเยี่ยม', 'จะมาอีก'],
                    4: ['อร่อยดี', 'ชอบมาก', 'ดีครับ', 'โอเค'],
                    3: ['ปกติ', 'ธรรมดา', 'พอใช้', 'โอเคครับ'],
                    2: ['ไม่ค่อยดี', 'ปรับปรุงได้', 'รสชาติธรรมดา', 'ช้าไป'],
                    1: ['ไม่อร่อย', 'ผิดหวัง', 'ไม่ประทับใจ', 'ปรับปรุงด่วน']
                }
                
                comment = random.choice(comments.get(rating, ['']))
                
                feedback = Feedback(
                    order_id=order.id,
                    rating=rating,
                    comment=comment,
                    created_at=order.completed_at + timedelta(minutes=random.randint(5, 120))
                )
                db.session.add(feedback)
            
            total_orders += 1
    
    db.session.commit()
    print(f"✅ Created {total_orders} historical orders")
    
    # Update analytics reports
    print("📈 Updating analytics reports...")
    for day_offset in range(30):
        target_date = (start_date + timedelta(days=day_offset)).date()
        update_daily_report(target_date)
        
        # Update hourly stats for each hour that had orders
        for hour in range(24):
            update_hourly_stats(target_date, hour)
        
        # Update menu popularity
        update_menu_popularity(target_date)
    
    print("✅ Analytics reports updated")

def main():
    """Main setup function"""
    
    print("🏪 LanAim POS System v2.4 - Phase 3 Setup")
    print("=" * 50)
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Drop and recreate all tables
            print("🗑️  Dropping existing tables...")
            db.drop_all()
            
            print("🏗️  Creating new tables...")
            db.create_all()
            
            # Create sample data
            create_sample_data()
            
            print("\n" + "=" * 50)
            print("✅ Phase 3 setup completed successfully!")
            print("\nDefault Login Credentials:")
            print("👤 Admin: username=admin, password=admin123")
            print("👨‍🍳 Kitchen: username=kitchen, password=kitchen123")
            print("🚴 Delivery: username=delivery, password=delivery123")
            print("\n🚀 You can now start the application with: python app.py")
            
        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    main()
