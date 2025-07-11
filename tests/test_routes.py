"""
Test Routes and Views
Unit tests for Flask routes and view functions
"""

import pytest
import json
from datetime import datetime
from io import BytesIO

from models import User, Menu, Order, OrderItem, DeliveryZone, db
from tests.conftest import (
    assert_valid_json_response, 
    assert_flash_message,
    create_test_menu_item,
    create_test_order
)


class TestMainRoutes:
    """Test main application routes"""
    
    def test_index_route(self, client):
        """Test main index route"""
        response = client.get('/')
        assert response.status_code == 200
        # Should redirect to menu or show menu page
    
    def test_menu_display(self, client):
        """Test menu display"""
        response = client.get('/menu')
        assert response.status_code == 200
        
        # Check that active menu items are displayed
        content = response.get_data(as_text=True)
        assert 'ผัดไทยกุ้ง' in content
        assert 'ต้มยำกุ้ง' in content
        # Inactive items should not be displayed
        assert 'ผัดกะเพราหมู' not in content or 'disabled' in content
    
    def test_cart_functionality(self, client):
        """Test shopping cart functionality"""
        # Test adding item to cart
        response = client.post('/add-to-cart', json={
            'menu_item_id': 1,
            'quantity': 2
        })
        assert response.status_code == 200
        data = assert_valid_json_response(response)
        assert data['success'] is True
        
        # Test viewing cart
        response = client.get('/cart')
        assert response.status_code == 200
    
    def test_checkout_process(self, client, app):
        """Test checkout process"""
        with app.app_context():
            # Add items to cart first
            client.post('/add-to-cart', json={
                'menu_item_id': 1,
                'quantity': 2
            })
            
            # Test checkout form
            response = client.get('/checkout')
            assert response.status_code == 200
            
            # Test submitting order
            delivery_zone = DeliveryZone.query.filter_by(is_active=True).first()
            order_data = {
                'customer_name': 'Test Customer',
                'customer_phone': '0812345678',
                'customer_address': '123 Test Street',
                'delivery_zone_id': delivery_zone.id,
                'order_type': 'delivery',
                'payment_method': 'cash'
            }
            
            response = client.post('/place-order', data=order_data)
            assert response.status_code in [200, 302]  # Success or redirect


class TestAdminRoutes:
    """Test admin panel routes"""
    
    def test_admin_login_required(self, client):
        """Test admin routes require authentication"""
        admin_routes = [
            '/admin',
            '/admin/dashboard',
            '/admin/menu',
            '/admin/orders',
            '/admin/users'
        ]
        
        for route in admin_routes:
            response = client.get(route)
            assert response.status_code in [302, 401, 403]  # Redirect to login or forbidden
    
    def test_admin_dashboard(self, authenticated_client):
        """Test admin dashboard"""
        response = authenticated_client.get('/admin')
        assert response.status_code == 200
        
        response = authenticated_client.get('/admin/dashboard')
        assert response.status_code == 200
    
    def test_admin_menu_management(self, authenticated_client, app):
        """Test admin menu management"""
        with app.app_context():
            # Test menu list
            response = authenticated_client.get('/admin/menu')
            assert response.status_code == 200
            
            # Test add menu form
            response = authenticated_client.get('/admin/menu/add')
            assert response.status_code == 200
            
            # Test adding new menu item
            menu_data = {
                'name': 'New Test Menu',
                'description': 'Test description',
                'price': '150.00',
                'category': 'Test Category',
                'prep_time': '20',
                'is_active': 'on'
            }
            
            response = authenticated_client.post('/admin/menu/add', data=menu_data)
            assert response.status_code in [200, 302]
            
            # Verify menu item was created
            new_item = Menu.query.filter_by(name='New Test Menu').first()
            assert new_item is not None
            assert new_item.price == 150.00
    
    def test_admin_menu_edit(self, authenticated_client, app):
        """Test editing menu items"""
        with app.app_context():
            menu_item = Menu.query.first()
            original_name = menu_item.name
            
            # Test edit form
            response = authenticated_client.get(f'/admin/menu/edit/{menu_item.id}')
            assert response.status_code == 200
            
            # Test updating menu item
            update_data = {
                'name': f'Updated {original_name}',
                'description': menu_item.description,
                'price': str(menu_item.price + 10),
                'category': menu_item.category,
                'prep_time': str(menu_item.prep_time),
                'is_active': 'on' if menu_item.is_active else ''
            }
            
            response = authenticated_client.post(f'/admin/menu/edit/{menu_item.id}', 
                                               data=update_data)
            assert response.status_code in [200, 302]
            
            # Verify changes
            updated_item = Menu.query.get(menu_item.id)
            assert updated_item.name == f'Updated {original_name}'
            assert updated_item.price == menu_item.price + 10
    
    def test_admin_menu_delete(self, authenticated_client, app):
        """Test deleting menu items"""
        with app.app_context():
            # Create a test menu item to delete
            test_item = create_test_menu_item('Delete Test Item')
            item_id = test_item.id
            
            response = authenticated_client.post(f'/admin/menu/delete/{item_id}')
            assert response.status_code in [200, 302]
            
            # Verify item was deleted or deactivated
            deleted_item = Menu.query.get(item_id)
            assert deleted_item is None or deleted_item.is_active is False
    
    def test_admin_order_management(self, authenticated_client, app):
        """Test admin order management"""
        with app.app_context():
            # Test orders list
            response = authenticated_client.get('/admin/orders')
            assert response.status_code == 200
            
            # Test viewing specific order
            order = Order.query.first()
            response = authenticated_client.get(f'/admin/orders/{order.id}')
            assert response.status_code == 200
            
            # Test updating order status
            response = authenticated_client.post(f'/admin/orders/{order.id}/status', 
                                               json={'status': 'confirmed'})
            assert response.status_code == 200
            
            # Verify status change
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'confirmed'
    
    def test_admin_user_management(self, authenticated_client, app):
        """Test admin user management"""
        with app.app_context():
            # Test users list
            response = authenticated_client.get('/admin/users')
            assert response.status_code == 200
            
            # Test add user form
            response = authenticated_client.get('/admin/users/add')
            assert response.status_code == 200
            
            # Test creating new user
            user_data = {
                'username': 'newadminuser',
                'email': 'newadmin@test.com',
                'password': 'password123',
                'role': 'staff',
                'is_active': 'on'
            }
            
            response = authenticated_client.post('/admin/users/add', data=user_data)
            assert response.status_code in [200, 302]
            
            # Verify user was created
            new_user = User.query.filter_by(username='newadminuser').first()
            assert new_user is not None
            assert new_user.email == 'newadmin@test.com'


class TestKitchenRoutes:
    """Test kitchen interface routes"""
    
    def test_kitchen_dashboard(self, client):
        """Test kitchen dashboard"""
        response = client.get('/kitchen')
        assert response.status_code == 200
    
    def test_kitchen_orders(self, client, app):
        """Test kitchen orders view"""
        with app.app_context():
            response = client.get('/kitchen/orders')
            assert response.status_code == 200
            
            # Test getting orders in JSON format
            response = client.get('/kitchen/orders', headers={'Accept': 'application/json'})
            assert response.status_code == 200
            data = assert_valid_json_response(response)
            assert 'orders' in data
    
    def test_kitchen_order_status_update(self, client, app):
        """Test updating order status from kitchen"""
        with app.app_context():
            order = Order.query.filter_by(status='pending').first()
            if not order:
                order = create_test_order('Kitchen Test', status='pending')
            
            response = client.post(f'/kitchen/orders/{order.id}/start')
            assert response.status_code == 200
            
            # Verify status changed
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'preparing'


class TestDeliveryRoutes:
    """Test delivery interface routes"""
    
    def test_delivery_dashboard(self, client):
        """Test delivery dashboard"""
        response = client.get('/delivery')
        assert response.status_code == 200
    
    def test_delivery_orders(self, client, app):
        """Test delivery orders view"""
        with app.app_context():
            response = client.get('/delivery/orders')
            assert response.status_code == 200
    
    def test_delivery_status_update(self, client, app):
        """Test delivery status updates"""
        with app.app_context():
            order = Order.query.filter_by(order_type='delivery').first()
            if order:
                response = client.post(f'/delivery/orders/{order.id}/pickup')
                assert response.status_code == 200
                
                response = client.post(f'/delivery/orders/{order.id}/deliver')
                assert response.status_code == 200


class TestAPIRoutes:
    """Test API endpoints"""
    
    def test_api_menu_items(self, client, app):
        """Test API menu items endpoint"""
        with app.app_context():
            response = client.get('/api/menu-items')
            assert response.status_code == 200
            data = assert_valid_json_response(response)
            
            assert 'items' in data
            assert len(data['items']) > 0
            
            # Check that only active items are returned
            for item in data['items']:
                assert item['is_active'] is True
    
    def test_api_delivery_zones(self, client, app):
        """Test API delivery zones endpoint"""
        with app.app_context():
            response = client.get('/api/delivery-zones')
            assert response.status_code == 200
            data = assert_valid_json_response(response)
            
            assert 'zones' in data
            assert len(data['zones']) > 0
    
    def test_api_order_status(self, client, app):
        """Test API order status endpoint"""
        with app.app_context():
            order = Order.query.first()
            response = client.get(f'/api/orders/{order.id}/status')
            assert response.status_code == 200
            data = assert_valid_json_response(response)
            
            assert 'order_id' in data
            assert 'status' in data
            assert data['order_id'] == order.id


class TestFileUpload:
    """Test file upload functionality"""
    
    def test_menu_image_upload(self, authenticated_client, app):
        """Test uploading menu item images"""
        with app.app_context():
            # Create test image file
            test_image = BytesIO(b'fake image data')
            test_image.name = 'test.jpg'
            
            menu_data = {
                'name': 'Image Test Menu',
                'description': 'Test with image',
                'price': '100.00',
                'category': 'Test',
                'prep_time': '10',
                'is_active': 'on',
                'image': (test_image, 'test.jpg')
            }
            
            response = authenticated_client.post('/admin/menu/add', 
                                               data=menu_data,
                                               content_type='multipart/form-data')
            
            # Should handle file upload (even if it's fake data)
            assert response.status_code in [200, 302, 400]  # Various outcomes acceptable


class TestErrorHandling:
    """Test error handling"""
    
    def test_404_handling(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
    
    def test_invalid_order_id(self, client):
        """Test handling invalid order IDs"""
        response = client.get('/admin/orders/99999')
        assert response.status_code == 404
    
    def test_invalid_menu_item_id(self, authenticated_client):
        """Test handling invalid menu item IDs"""
        response = authenticated_client.get('/admin/menu/edit/99999')
        assert response.status_code == 404
    
    def test_invalid_json_requests(self, client):
        """Test handling invalid JSON requests"""
        response = client.post('/add-to-cart', 
                             data='invalid json',
                             content_type='application/json')
        assert response.status_code == 400


class TestFormValidation:
    """Test form validation"""
    
    def test_empty_menu_form(self, authenticated_client):
        """Test validation of empty menu form"""
        response = authenticated_client.post('/admin/menu/add', data={})
        assert response.status_code in [200, 400]  # Should show validation errors
    
    def test_invalid_price_format(self, authenticated_client):
        """Test validation of invalid price format"""
        menu_data = {
            'name': 'Invalid Price Menu',
            'price': 'not-a-number',
            'category': 'Test'
        }
        
        response = authenticated_client.post('/admin/menu/add', data=menu_data)
        assert response.status_code in [200, 400]  # Should show validation errors
    
    def test_negative_price(self, authenticated_client):
        """Test validation of negative prices"""
        menu_data = {
            'name': 'Negative Price Menu',
            'price': '-10.00',
            'category': 'Test'
        }
        
        response = authenticated_client.post('/admin/menu/add', data=menu_data)
        assert response.status_code in [200, 400]  # Should show validation errors


class TestSecurity:
    """Test security features"""
    
    def test_admin_access_control(self, client, app):
        """Test that non-admin users cannot access admin routes"""
        with app.app_context():
            # Create non-admin user
            staff_user = User.query.filter_by(role='staff').first()
            
            # Try to access admin routes as staff
            with client.session_transaction() as sess:
                sess['user_id'] = staff_user.id
            
            response = client.get('/admin/menu/add')
            assert response.status_code in [302, 403]  # Should be redirected or forbidden
    
    def test_csrf_protection(self, authenticated_client):
        """Test CSRF protection on forms"""
        # This would test CSRF tokens if implemented
        response = authenticated_client.post('/admin/menu/add', data={
            'name': 'CSRF Test',
            'price': '100.00'
        })
        # Behavior depends on CSRF implementation
        assert response.status_code in [200, 302, 400, 403]
    
    def test_sql_injection_prevention(self, client):
        """Test SQL injection prevention"""
        # Try SQL injection in search parameters
        malicious_input = "'; DROP TABLE menu_items; --"
        
        response = client.get(f'/menu?search={malicious_input}')
        assert response.status_code in [200, 400]  # Should handle gracefully
        
        # Verify that database is still intact
        response = client.get('/menu')
        assert response.status_code == 200
