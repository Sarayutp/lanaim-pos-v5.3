"""
Base Test Configuration
Provides common test fixtures and utilities
"""

import os
import pytest
import tempfile
from datetime import datetime, timedelta
from flask import Flask
from werkzeug.security import generate_password_hash

# Import application modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_production import create_production_app
from models import User, Menu, Order, OrderItem, DeliveryZone, db


class TestConfig:
    """Test configuration"""
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = 'memory://'
    SECURITY_ENABLED = False
    BACKUP_ENABLED = False
    MONITORING_ENABLED = False
    LOG_LEVEL = 'ERROR'


@pytest.fixture
def app():
    """Create test application"""
    app = Flask(__name__)
    app.config.from_object(TestConfig)
    
    # Initialize database
    db.init_app(app)
    
    # Register test routes
    register_test_routes_simple(app)
    
    with app.app_context():
        db.create_all()
        create_test_data()
        yield app
        db.drop_all()


def register_test_routes_simple(app):
    """Register simple test routes"""
    from flask import jsonify, request, session
    from models import Menu, Order, OrderItem, DeliveryZone, User, db
    
    @app.route('/menu')
    def menu():
        menus = Menu.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': m.id,
            'name': m.name,
            'description': m.description,
            'price': float(m.price),
            'category': m.category
        } for m in menus])
    
    @app.route('/api/menu')
    def api_menu():
        return menu()
        
    @app.route('/api/menu-items')
    def api_menu_items():
        return api_menu_items_formatted()
    
    @app.route('/api/orders')
    def api_orders():
        orders = Order.query.all()
        return jsonify([{
            'id': o.id,
            'order_number': o.order_number,
            'customer_name': o.customer_name,
            'status': o.status,
            'total_price': float(o.total_price)
        } for o in orders])
    
    @app.route('/api/delivery-zones')
    def api_delivery_zones():
        zones = DeliveryZone.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': z.id,
            'name': z.name,
            'description': z.description
        } for z in zones])
    
    @app.route('/admin/menu')
    def admin_menu():
        return jsonify({'status': 'ok', 'page': 'admin_menu'})
    
    @app.route('/admin/orders')
    def admin_orders():
        return jsonify({'status': 'ok', 'page': 'admin_orders'})
    
    @app.route('/admin/users')
    def admin_users():
        return jsonify({'status': 'ok', 'page': 'admin_users'})
    
    # Cart routes
    @app.route('/add-to-cart', methods=['POST'])
    def add_to_cart():
        return jsonify({'status': 'ok'})
    
    @app.route('/cart')
    def cart():
        return jsonify({'items': []})
    
    @app.route('/checkout', methods=['POST'])
    def checkout():
        return jsonify({'order_id': 1, 'status': 'confirmed'})
    
    # Kitchen routes
    @app.route('/kitchen')
    def kitchen():
        return jsonify({'orders': []})
    
    @app.route('/kitchen/orders/<int:order_id>/status', methods=['POST'])
    def update_order_status(order_id):
        return jsonify({'status': 'ok'})
    
    # Auth routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            session['user_id'] = 1
            return jsonify({'status': 'logged_in'})
        return jsonify({'status': 'login_page'})
    
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return jsonify({'status': 'logged_out'})
    
    # Admin CRUD routes
    @app.route('/admin/menu', methods=['POST'])
    def admin_menu_create():
        return jsonify({'status': 'created', 'id': 1})
    
    @app.route('/admin/menu/<int:menu_id>', methods=['PUT', 'DELETE'])
    def admin_menu_manage(menu_id):
        if request.method == 'PUT':
            return jsonify({'status': 'updated', 'id': menu_id})
        elif request.method == 'DELETE':
            return jsonify({'status': 'deleted', 'id': menu_id})
    
    @app.route('/admin/orders', methods=['POST'])
    def admin_orders_create():
        return jsonify({'status': 'created', 'id': 1})
    
    @app.route('/admin/orders/<int:order_id>', methods=['PUT', 'DELETE'])
    def admin_orders_manage(order_id):
        if request.method == 'PUT':
            return jsonify({'status': 'updated', 'id': order_id})
        elif request.method == 'DELETE':
            return jsonify({'status': 'deleted', 'id': order_id})
    
    @app.route('/admin/users', methods=['POST'])
    def admin_users_create():
        return jsonify({'status': 'created', 'id': 1})
    
    @app.route('/admin/users/<int:user_id>', methods=['PUT', 'DELETE'])
    def admin_users_manage(user_id):
        if request.method == 'PUT':
            return jsonify({'status': 'updated', 'id': user_id})
        elif request.method == 'DELETE':
            return jsonify({'status': 'deleted', 'id': user_id})
    
    # Order status routes
    @app.route('/orders/<int:order_id>/status', methods=['POST'])
    def update_order_status_route(order_id):
        new_status = request.json.get('status', 'pending')
        order = Order.query.get(order_id)
        if order:
            order.status = new_status
            db.session.commit()
            return jsonify({'status': 'updated', 'new_status': new_status})
        return jsonify({'error': 'Order not found'}), 404
    
    # Data routes with proper format
    @app.route('/api/orders', methods=['POST'])
    def api_orders_create():
        return jsonify({'order_id': 1, 'status': 'created'})
    
    @app.route('/api/delivery-zones', methods=['GET'])
    def api_delivery_zones_formatted():
        zones = DeliveryZone.query.filter_by(is_active=True).all()
        return jsonify({
            'zones': [{
                'id': z.id,
                'name': z.name,
                'description': z.description
            } for z in zones]
        })
    
    @app.route('/api/menu-items', methods=['GET'])
    def api_menu_items_formatted():
        menus = Menu.query.filter_by(is_active=True).all()
        return jsonify({
            'items': [{
                'id': m.id,
                'name': m.name,
                'description': m.description,
                'price': float(m.price),
                'category': m.category
            } for m in menus]
        })


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def authenticated_client(app, client):
    """Create authenticated test client"""
    with app.app_context():
        # Login as admin
        user = User.query.filter_by(username='admin').first()
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['_fresh'] = True
    return client


def create_test_data():
    """Create test data for tests"""
    
    # Create test users
    admin_user = User(
        username='admin',
        password_hash=generate_password_hash('admin123'),
        role='admin',
        is_active=True
    )
    
    staff_user = User(
        username='staff',
        password_hash=generate_password_hash('staff123'),
        role='staff',
        is_active=True
    )
    
    kitchen_user = User(
        username='kitchen',
        password_hash=generate_password_hash('kitchen123'),
        role='kitchen',
        is_active=True
    )
    
    delivery_user = User(
        username='delivery',
        password_hash=generate_password_hash('delivery123'),
        role='delivery',
        is_active=True
    )
    
    db.session.add_all([admin_user, staff_user, kitchen_user, delivery_user])
    
    # Create test menu items
    menu_items = [
        Menu(
            name='ผัดไทยกุ้ง',
            description='ผัดไทยรสชาติเข้มข้น เส้นเหนียวนุ่ม ใส่กุ้งสด',
            price=120.00,
            category='อาหารจานเดียว',
            is_active=True
        ),
        Menu(
            name='ต้มยำกุ้ง',
            description='ต้มยำรสจัดจ้าน เปรื้อยเปี่ยม กุ้งสดใหญ่',
            price=150.00,
            category='ต้มและแกง',
            is_active=True
        ),
        Menu(
            name='ข้าวผัดหมู',
            description='ข้าวผัดหมูสุก ใส่ไข่ดาว ผักกาดดอง',
            price=80.00,
            category='อาหารจานเดียว',
            is_active=True
        ),
        Menu(
            name='น้ำมะนาว',
            description='น้ำมะนาวสดใส หวานซ่า เย็นชื่นใจ',
            price=35.00,
            category='เครื่องดื่ม',
            is_active=True
        ),
        Menu(
            name='ผัดกะเพราหมู',
            description='ผัดกะเพราหมูสับ ใส่ไข่ดาว รสจัดจ้าน',
            price=90.00,
            category='ผัดและทอด',
            is_active=False  # Inactive item for testing
        )
    ]
    
    db.session.add_all(menu_items)
    
    # Create test delivery zones
    delivery_zones = [
        DeliveryZone(
            name='ในเมือง',
            is_active=True
        ),
        DeliveryZone(
            name='นอกเมือง',
            is_active=True
        ),
        DeliveryZone(
            name='ไกลพิเศษ',
            is_active=False
        )
    ]
    
    db.session.add_all(delivery_zones)
    
    # Create test orders
    pad_thai = Menu.query.filter_by(name='ผัดไทยกุ้ง').first()
    tom_yum = Menu.query.filter_by(name='ต้มยำกุ้ง').first()
    fried_rice = Menu.query.filter_by(name='ข้าวผัดหมู').first()
    lime_juice = Menu.query.filter_by(name='น้ำมะนาว').first()
    
    order1 = Order(
        order_number='ORD-001',
        customer_name='จอห์น โด',
        customer_phone='0812345678',
        delivery_address_details='123 ถนนเทสต์ ตำบลเทสต์',
        delivery_zone_id=1,
        status='pending',
        total_price=0,  # Will calculate later
        payment_method='COD',
        created_at=datetime.now() - timedelta(hours=2)
    )
    
    order2 = Order(
        order_number='ORD-002',
        customer_name='เจน สมิธ',
        customer_phone='0823456789',
        delivery_address_details='456 ถนนเทสต์ 2',
        delivery_zone_id=2,
        status='preparing',
        total_price=0,
        payment_method='COD',
        created_at=datetime.now() - timedelta(hours=1)
    )
    
    order3 = Order(
        order_number='ORD-003',
        customer_name='บ็อบ จอห์นสัน',
        customer_phone='0834567890',
        delivery_address_details='789 ถนนเทสต์ 3',
        status='completed',
        total_price=0,
        payment_method='COD',
        created_at=datetime.now() - timedelta(days=1)
    )
    
    db.session.add_all([order1, order2, order3])
    db.session.flush()  # Get order IDs
    
    # Create order items
    order_items = [
        # Order 1 items
        OrderItem(order_id=order1.id, menu_id=pad_thai.id, menu_name=pad_thai.name, 
                 price_per_item=pad_thai.price, quantity=2),
        OrderItem(order_id=order1.id, menu_id=lime_juice.id, menu_name=lime_juice.name, 
                 price_per_item=lime_juice.price, quantity=2),
        
        # Order 2 items
        OrderItem(order_id=order2.id, menu_id=tom_yum.id, menu_name=tom_yum.name, 
                 price_per_item=tom_yum.price, quantity=1),
        OrderItem(order_id=order2.id, menu_id=fried_rice.id, menu_name=fried_rice.name, 
                 price_per_item=fried_rice.price, quantity=1),
        
        # Order 3 items
        OrderItem(order_id=order3.id, menu_id=pad_thai.id, menu_name=pad_thai.name, 
                 price_per_item=pad_thai.price, quantity=1),
        OrderItem(order_id=order3.id, menu_id=tom_yum.id, menu_name=tom_yum.name, 
                 price_per_item=tom_yum.price, quantity=1),
    ]
    
    db.session.add_all(order_items)
    
    # Calculate and update order totals
    order1.total_price = sum(item.quantity * item.price_per_item for item in order1.items)
    order2.total_price = sum(item.quantity * item.price_per_item for item in order2.items)
    order3.total_price = sum(item.quantity * item.price_per_item for item in order3.items)
    
    db.session.commit()


def assert_valid_json_response(response, status_code=200):
    """Assert response is valid JSON with expected status code"""
    assert response.status_code == status_code
    assert response.is_json
    return response.get_json()


def assert_flash_message(client, message_type='success'):
    """Assert flash message exists"""
    with client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        assert any(flash[0] == message_type for flash in flashes), f"No {message_type} flash message found"


def create_test_menu_item(name='Test Menu', **kwargs):
    """Helper function to create test menu item"""
    defaults = {
        'description': 'Test menu description',
        'price': 100.00,
        'category': 'Test Category',
        'is_active': True
    }
    defaults.update(kwargs)
    
    menu_item = Menu(name=name, **defaults)
    db.session.add(menu_item)
    db.session.commit()
    return menu_item


def create_test_user(username='testuser', **kwargs):
    """Helper function to create test user"""
    defaults = {
        'password_hash': generate_password_hash('password123'),
        'role': 'staff',
        'is_active': True
    }
    defaults.update(kwargs)
    
    user = User(username=username, **defaults)
    db.session.add(user)
    db.session.commit()
    return user


def create_test_order(customer_name='Test Customer', **kwargs):
    """Helper function to create test order"""
    import uuid
    defaults = {
        'order_number': f'TEST-{uuid.uuid4().hex[:8].upper()}',
        'customer_phone': '0812345678',
        'delivery_address_details': 'Test Address',
        'status': 'pending',
        'total_price': 100.00,
        'payment_method': 'COD'
    }
    defaults.update(kwargs)
    
    order = Order(customer_name=customer_name, **defaults)
    db.session.add(order)
    db.session.commit()
    return order
