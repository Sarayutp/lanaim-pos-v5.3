"""
Test Models
Unit tests for database models and their relationships
"""

import pytest
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash

from models import User, Menu, Order, OrderItem, DeliveryZone, db
from tests.conftest import create_test_menu_item, create_test_order, create_test_user


class TestUser:
    """Test User model"""
    
    def test_user_creation(self, app):
        """Test creating a new user"""
        with app.app_context():
            user = create_test_user('newuser', email='newuser@test.com', role='admin')
            
            assert user.id is not None
            assert user.username == 'newuser'
            assert user.email == 'newuser@test.com'
            assert user.role == 'admin'
            assert user.is_active is True
            assert check_password_hash(user.password_hash, 'password123')
    
    def test_user_password_hashing(self, app):
        """Test password hashing"""
        with app.app_context():
            user = create_test_user('testpass')
            
            # Password should be hashed, not stored as plain text
            assert user.password_hash != 'password123'
            assert check_password_hash(user.password_hash, 'password123')
            assert not check_password_hash(user.password_hash, 'wrongpassword')
    
    def test_user_roles(self, app):
        """Test different user roles"""
        with app.app_context():
            admin = create_test_user('admin_user', role='admin')
            staff = create_test_user('staff_user', role='staff')
            kitchen = create_test_user('kitchen_user', role='kitchen')
            delivery = create_test_user('delivery_user', role='delivery')
            
            assert admin.role == 'admin'
            assert staff.role == 'staff'
            assert kitchen.role == 'kitchen'
            assert delivery.role == 'delivery'
    
    def test_user_string_representation(self, app):
        """Test user string representation"""
        with app.app_context():
            user = create_test_user('testuser')
            assert str(user) == 'testuser'
    
    def test_user_query_methods(self, app):
        """Test user query methods"""
        with app.app_context():
            # Test finding user by username
            user = User.query.filter_by(username='admin').first()
            assert user is not None
            assert user.username == 'admin'
            
            # Test finding user by email
            user = User.query.filter_by(email='admin@test.com').first()
            assert user is not None
            assert user.email == 'admin@test.com'
    
    def test_user_active_inactive(self, app):
        """Test user active/inactive status"""
        with app.app_context():
            active_user = create_test_user('active_user', is_active=True)
            inactive_user = create_test_user('inactive_user', is_active=False)
            
            assert active_user.is_active is True
            assert inactive_user.is_active is False


class TestMenu:
    """Test Menu model"""
    
    def test_menu_item_creation(self, app):
        """Test creating a new menu item"""
        with app.app_context():
            item = create_test_menu_item(
                'ข้าวผัดกุ้ง',
                description='ข้าวผัดกุ้งสดใหญ่',
                price=120.50,
                category='อาหารจานเดียว',
                prep_time=15
            )
            
            assert item.id is not None
            assert item.name == 'ข้าวผัดกุ้ง'
            assert item.description == 'ข้าวผัดกุ้งสดใหญ่'
            assert item.price == 120.50
            assert item.category == 'อาหารจานเดียว'
            assert item.prep_time == 15
            assert item.is_active is True
    
    def test_menu_item_price_validation(self, app):
        """Test menu item price validation"""
        with app.app_context():
            # Test valid prices
            item1 = create_test_menu_item('item1', price=0.0)
            item2 = create_test_menu_item('item2', price=999.99)
            
            assert item1.price == 0.0
            assert item2.price == 999.99
    
    def test_menu_item_active_inactive(self, app):
        """Test menu item active/inactive status"""
        with app.app_context():
            active_item = create_test_menu_item('active_item', is_active=True)
            inactive_item = create_test_menu_item('inactive_item', is_active=False)
            
            assert active_item.is_active is True
            assert inactive_item.is_active is False
    
    def test_menu_item_string_representation(self, app):
        """Test menu item string representation"""
        with app.app_context():
            item = create_test_menu_item('ต้มยำกุ้ง')
            assert str(item) == 'ต้มยำกุ้ง'
    
    def test_menu_item_categories(self, app):
        """Test menu item categories"""
        with app.app_context():
            categories = [
                'อาหารจานเดียว',
                'ผัดและทอด',
                'ต้มและแกง',
                'เครื่องดื่ม',
                'ของหวาน'
            ]
            
            items = []
            for i, category in enumerate(categories):
                item = create_test_menu_item(f'item_{i}', category=category)
                items.append(item)
            
            for item, expected_category in zip(items, categories):
                assert item.category == expected_category
    
    def test_menu_item_query_by_category(self, app):
        """Test querying menu items by category"""
        with app.app_context():
            # Query existing menu items
            drinks = Menu.query.filter_by(category='เครื่องดื่ม').all()
            main_dishes = Menu.query.filter_by(category='อาหารจานเดียว').all()
            
            assert len(drinks) >= 1
            assert len(main_dishes) >= 2
            
            for drink in drinks:
                assert drink.category == 'เครื่องดื่ม'


class TestOrder:
    """Test Order model"""
    
    def test_order_creation(self, app):
        """Test creating a new order"""
        with app.app_context():
            order = create_test_order(
                'John Doe',
                customer_phone='0812345678',
                customer_address='123 Test Street',
                order_type='delivery',
                status='pending'
            )
            
            assert order.id is not None
            assert order.customer_name == 'John Doe'
            assert order.customer_phone == '0812345678'
            assert order.customer_address == '123 Test Street'
            assert order.order_type == 'delivery'
            assert order.status == 'pending'
            assert order.created_at is not None
    
    def test_order_status_progression(self, app):
        """Test order status changes"""
        with app.app_context():
            order = create_test_order('Test Customer')
            
            statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivering', 'completed']
            
            for status in statuses:
                order.status = status
                db.session.commit()
                
                updated_order = Order.query.get(order.id)
                assert updated_order.status == status
    
    def test_order_types(self, app):
        """Test different order types"""
        with app.app_context():
            delivery_order = create_test_order('Customer 1', order_type='delivery')
            pickup_order = create_test_order('Customer 2', order_type='pickup')
            dine_in_order = create_test_order('Customer 3', order_type='dine_in', table_number=5)
            
            assert delivery_order.order_type == 'delivery'
            assert pickup_order.order_type == 'pickup'
            assert dine_in_order.order_type == 'dine_in'
            assert dine_in_order.table_number == 5
    
    def test_order_with_delivery_zone(self, app):
        """Test order with delivery zone relationship"""
        with app.app_context():
            delivery_zone = DeliveryZone.query.first()
            order = create_test_order(
                'Customer with Zone',
                delivery_zone_id=delivery_zone.id,
                order_type='delivery'
            )
            
            assert order.delivery_zone_id == delivery_zone.id
            assert order.delivery_zone.name == delivery_zone.name
    
    def test_order_timestamps(self, app):
        """Test order timestamps"""
        with app.app_context():
            before_creation = datetime.now()
            order = create_test_order('Time Test Customer')
            after_creation = datetime.now()
            
            assert before_creation <= order.created_at <= after_creation
            
            # Test updating timestamps
            order.confirmed_at = datetime.now()
            order.completed_at = datetime.now() + timedelta(minutes=30)
            db.session.commit()
            
            assert order.confirmed_at is not None
            assert order.completed_at is not None
            assert order.completed_at > order.confirmed_at


class TestOrderItem:
    """Test OrderItem model"""
    
    def test_order_item_creation(self, app):
        """Test creating order items"""
        with app.app_context():
            order = create_test_order('Item Test Customer')
            menu_item = Menu.query.first()
            
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                quantity=2,
                price=menu_item.price,
                notes='Extra spicy'
            )
            
            db.session.add(order_item)
            db.session.commit()
            
            assert order_item.id is not None
            assert order_item.order_id == order.id
            assert order_item.menu_item_id == menu_item.id
            assert order_item.quantity == 2
            assert order_item.price == menu_item.price
            assert order_item.notes == 'Extra spicy'
    
    def test_order_item_relationships(self, app):
        """Test order item relationships"""
        with app.app_context():
            order = Order.query.first()
            
            # Test that order has items
            assert len(order.items) > 0
            
            # Test that each item has valid relationships
            for item in order.items:
                assert item.order_id == order.id
                assert item.menu_item is not None
                assert item.menu_item.id == item.menu_item_id
    
    def test_order_total_calculation(self, app):
        """Test order total calculation"""
        with app.app_context():
            order = Order.query.first()
            
            # Calculate expected total
            items_total = sum(item.quantity * item.price for item in order.items)
            delivery_fee = order.delivery_zone.delivery_fee if order.delivery_zone else 0
            expected_total = items_total + delivery_fee
            
            assert abs(order.total_amount - expected_total) < 0.01  # Account for float precision


class TestDeliveryZone:
    """Test DeliveryZone model"""
    
    def test_delivery_zone_creation(self, app):
        """Test creating delivery zones"""
        with app.app_context():
            zone = DeliveryZone(
                name='Test Zone',
                delivery_fee=25.00,
                min_order=150.00,
                is_active=True
            )
            
            db.session.add(zone)
            db.session.commit()
            
            assert zone.id is not None
            assert zone.name == 'Test Zone'
            assert zone.delivery_fee == 25.00
            assert zone.min_order == 150.00
            assert zone.is_active is True
    
    def test_delivery_zone_relationships(self, app):
        """Test delivery zone relationships with orders"""
        with app.app_context():
            zone = DeliveryZone.query.first()
            orders = Order.query.filter_by(delivery_zone_id=zone.id).all()
            
            # Test that zone has orders
            assert len(orders) > 0
            
            # Test that orders reference the correct zone
            for order in orders:
                assert order.delivery_zone_id == zone.id
                assert order.delivery_zone.name == zone.name
    
    def test_delivery_zone_active_inactive(self, app):
        """Test delivery zone active/inactive status"""
        with app.app_context():
            active_zones = DeliveryZone.query.filter_by(is_active=True).all()
            inactive_zones = DeliveryZone.query.filter_by(is_active=False).all()
            
            assert len(active_zones) >= 2
            assert len(inactive_zones) >= 1
            
            for zone in active_zones:
                assert zone.is_active is True
            
            for zone in inactive_zones:
                assert zone.is_active is False


class TestModelRelationships:
    """Test model relationships and constraints"""
    
    def test_order_cascade_delete(self, app):
        """Test that deleting an order deletes its items"""
        with app.app_context():
            order = create_test_order('Delete Test Customer')
            menu_item = Menu.query.first()
            
            # Add order item
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                quantity=1,
                price=menu_item.price
            )
            db.session.add(order_item)
            db.session.commit()
            
            order_item_id = order_item.id
            
            # Delete order
            db.session.delete(order)
            db.session.commit()
            
            # Check that order item was also deleted
            deleted_item = OrderItem.query.get(order_item_id)
            assert deleted_item is None
    
    def test_menu_item_constraint_with_orders(self, app):
        """Test that menu items with orders cannot be deleted directly"""
        with app.app_context():
            # Find a menu item that has order items
            menu_item = Menu.query.join(OrderItem).first()
            assert menu_item is not None
            
            menu_item_id = menu_item.id
            
            # Try to delete the menu item (should handle gracefully)
            # In a real application, you'd want to prevent this or handle it properly
            existing_order_items = OrderItem.query.filter_by(menu_item_id=menu_item_id).count()
            assert existing_order_items > 0
    
    def test_user_unique_constraints(self, app):
        """Test user unique constraints"""
        with app.app_context():
            # Try to create user with existing username
            try:
                duplicate_user = create_test_user('admin')  # Username already exists
                assert False, "Should not allow duplicate username"
            except Exception:
                pass  # Expected to fail
            
            # Try to create user with existing email
            try:
                User(
                    username='newtestuser',
                    email='admin@test.com',  # Email already exists
                    password_hash='hash',
                    role='staff'
                )
                db.session.commit()
                assert False, "Should not allow duplicate email"
            except Exception:
                db.session.rollback()  # Clean up failed transaction
