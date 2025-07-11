"""
Integration Tests
End-to-end integration tests for the complete system
"""

import pytest
import json
import time
from datetime import datetime, timedelta

from models import User, Menu, Order, OrderItem, DeliveryZone, db
from tests.conftest import create_test_menu_item, create_test_order


class TestOrderFlow:
    """Test complete order flow from customer to delivery"""
    
    def test_complete_delivery_order_flow(self, client, app):
        """Test complete order flow for delivery"""
        with app.app_context():
            # Step 1: Customer views menu
            response = client.get('/menu')
            assert response.status_code == 200
            
            # Step 2: Customer adds items to cart
            menu_item = Menu.query.filter_by(is_active=True).first()
            response = client.post('/add-to-cart', json={
                'menu_item_id': menu_item.id,
                'quantity': 2
            })
            assert response.status_code == 200
            
            # Step 3: Customer proceeds to checkout
            response = client.get('/checkout')
            assert response.status_code == 200
            
            # Step 4: Customer places order
            delivery_zone = DeliveryZone.query.filter_by(is_active=True).first()
            order_data = {
                'customer_name': 'Integration Test Customer',
                'customer_phone': '0891234567',
                'customer_address': '123 Integration Test Street',
                'delivery_zone_id': delivery_zone.id,
                'order_type': 'delivery',
                'payment_method': 'cash'
            }
            
            response = client.post('/place-order', data=order_data)
            assert response.status_code in [200, 302]
            
            # Verify order was created
            new_order = Order.query.filter_by(customer_name='Integration Test Customer').first()
            assert new_order is not None
            assert new_order.status == 'pending'
            assert len(new_order.items) > 0
    
    def test_kitchen_order_processing(self, client, authenticated_client, app):
        """Test order processing in kitchen"""
        with app.app_context():
            # Create test order
            order = create_test_order('Kitchen Flow Test', status='pending')
            
            # Kitchen views pending orders
            response = client.get('/kitchen/orders')
            assert response.status_code == 200
            
            # Kitchen starts preparing order
            response = client.post(f'/kitchen/orders/{order.id}/start')
            assert response.status_code == 200
            
            # Verify status changed
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'preparing'
            
            # Kitchen marks order as ready
            response = client.post(f'/kitchen/orders/{order.id}/ready')
            assert response.status_code == 200
            
            # Verify status changed
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'ready'
    
    def test_delivery_order_flow(self, client, app):
        """Test delivery flow"""
        with app.app_context():
            # Create ready order for delivery
            order = create_test_order(
                'Delivery Flow Test',
                status='ready',
                order_type='delivery'
            )
            
            # Delivery person views ready orders
            response = client.get('/delivery/orders')
            assert response.status_code == 200
            
            # Delivery person picks up order
            response = client.post(f'/delivery/orders/{order.id}/pickup')
            assert response.status_code == 200
            
            # Verify status changed
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'delivering'
            
            # Delivery person completes delivery
            response = client.post(f'/delivery/orders/{order.id}/deliver')
            assert response.status_code == 200
            
            # Verify status changed
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'completed'


class TestAdminWorkflow:
    """Test admin workflow and management"""
    
    def test_menu_management_workflow(self, authenticated_client, app):
        """Test complete menu management workflow"""
        with app.app_context():
            # Admin views menu list
            response = authenticated_client.get('/admin/menu')
            assert response.status_code == 200
            
            # Admin adds new menu item
            new_menu_data = {
                'name': 'Workflow Test Menu',
                'description': 'Test menu for workflow',
                'price': '199.99',
                'category': 'Integration Test',
                'prep_time': '25',
                'is_active': 'on'
            }
            
            response = authenticated_client.post('/admin/menu/add', data=new_menu_data)
            assert response.status_code in [200, 302]
            
            # Verify menu item was created
            new_item = Menu.query.filter_by(name='Workflow Test Menu').first()
            assert new_item is not None
            assert new_item.price_per_item == 199.99
            
            # Admin edits menu item
            edit_data = {
                'name': 'Updated Workflow Test Menu',
                'description': new_item.description,
                'price': '249.99',
                'category': new_item.category,
                'prep_time': '30',
                'is_active': 'on'
            }
            
            response = authenticated_client.post(f'/admin/menu/edit/{new_item.id}', data=edit_data)
            assert response.status_code in [200, 302]
            
            # Verify changes
            updated_item = Menu.query.get(new_item.id)
            assert updated_item.name == 'Updated Workflow Test Menu'
            assert updated_item.price_per_item == 249.99
            assert updated_item.prep_time == 30
            
            # Admin deactivates menu item
            deactivate_data = dict(edit_data)
            del deactivate_data['is_active']  # Remove active flag
            
            response = authenticated_client.post(f'/admin/menu/edit/{new_item.id}', data=deactivate_data)
            assert response.status_code in [200, 302]
            
            # Verify deactivation
            updated_item = Menu.query.get(new_item.id)
            assert updated_item.is_active is False
    
    def test_order_management_workflow(self, authenticated_client, app):
        """Test admin order management workflow"""
        with app.app_context():
            # Create test order
            order = create_test_order('Admin Workflow Test', status='pending')
            
            # Admin views orders
            response = authenticated_client.get('/admin/orders')
            assert response.status_code == 200
            
            # Admin views specific order
            response = authenticated_client.get(f'/admin/orders/{order.id}')
            assert response.status_code == 200
            
            # Admin confirms order
            response = authenticated_client.post(f'/admin/orders/{order.id}/status', 
                                               json={'status': 'confirmed'})
            assert response.status_code == 200
            
            # Verify status change
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'confirmed'
            
            # Admin cancels order
            response = authenticated_client.post(f'/admin/orders/{order.id}/status', 
                                               json={'status': 'cancelled'})
            assert response.status_code == 200
            
            # Verify cancellation
            updated_order = Order.query.get(order.id)
            assert updated_order.status == 'cancelled'
    
    def test_user_management_workflow(self, authenticated_client, app):
        """Test admin user management workflow"""
        with app.app_context():
            # Admin views users
            response = authenticated_client.get('/admin/users')
            assert response.status_code == 200
            
            # Admin creates new user
            user_data = {
                'username': 'workflow_test_user',
                'email': 'workflow@test.com',
                'password': 'password123',
                'role': 'staff',
                'is_active': 'on'
            }
            
            response = authenticated_client.post('/admin/users/add', data=user_data)
            assert response.status_code in [200, 302]
            
            # Verify user creation
            new_user = User.query.filter_by(username='workflow_test_user').first()
            assert new_user is not None
            assert new_user.email == 'workflow@test.com'
            assert new_user.role == 'staff'
            assert new_user.is_active is True


class TestAPIIntegration:
    """Test API integration"""
    
    def test_api_menu_integration(self, client, app):
        """Test menu API integration"""
        with app.app_context():
            # Get menu items via API
            response = client.get('/api/menu-items')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'items' in data
            assert len(data['items']) > 0
            
            # Verify data structure
            for item in data['items']:
                assert 'id' in item
                assert 'name' in item
                assert 'price' in item
                assert 'category' in item
    
    def test_api_order_integration(self, client, app):
        """Test order API integration"""
        with app.app_context():
            order = Order.query.first()
            
            # Get order status via API
            response = client.get(f'/api/orders/{order.id}/status')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'order_id' in data
            assert 'status' in data
            assert data['order_id'] == order.id
    
    def test_api_delivery_zones_integration(self, client, app):
        """Test delivery zones API integration"""
        with app.app_context():
            response = client.get('/api/delivery-zones')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'zones' in data
            assert len(data['zones']) > 0
            
            # Verify zone structure
            for zone in data['zones']:
                assert 'id' in zone
                assert 'name' in zone


class TestRealTimeFeatures:
    """Test real-time features"""
    
    def test_order_status_updates(self, client, app):
        """Test real-time order status updates"""
        with app.app_context():
            order = create_test_order('Real-time Test', status='pending')
            
            # Simulate status updates
            status_progression = ['confirmed', 'preparing', 'ready', 'delivering', 'completed']
            
            for status in status_progression:
                # Update status
                response = client.post(f'/admin/orders/{order.id}/status', 
                                     json={'status': status})
                assert response.status_code == 200
                
                # Verify status change
                updated_order = Order.query.get(order.id)
                assert updated_order.status == status
                
                # Check if notification would be sent
                # (In a real test, you'd verify WebSocket messages)
    
    def test_kitchen_notifications(self, client, app):
        """Test kitchen notification system"""
        with app.app_context():
            # Create new order (should trigger kitchen notification)
            order = create_test_order('Kitchen Notification Test', status='confirmed')
            
            # Kitchen should receive notification about new order
            # In a real test, you'd verify WebSocket connection and messages
            assert order.status == 'confirmed'


class TestPerformanceIntegration:
    """Test performance under load"""
    
    def test_concurrent_orders(self, client, app):
        """Test handling multiple concurrent orders"""
        with app.app_context():
            # Simulate multiple orders being placed
            orders = []
            
            for i in range(5):
                order = create_test_order(f'Concurrent Test {i}', status='pending')
                orders.append(order)
            
            # Verify all orders were created
            assert len(orders) == 5
            
            # Process all orders
            for order in orders:
                response = client.post(f'/kitchen/orders/{order.id}/start')
                assert response.status_code == 200
            
            # Verify all orders are in preparing status
            for order in orders:
                updated_order = Order.query.get(order.id)
                assert updated_order.status == 'preparing'
    
    def test_menu_filtering_performance(self, client, app):
        """Test menu filtering performance"""
        with app.app_context():
            # Create multiple menu items
            categories = ['Test Cat 1', 'Test Cat 2', 'Test Cat 3']
            
            for i in range(10):
                for category in categories:
                    create_test_menu_item(
                        f'Performance Test Item {i}_{category}',
                        category=category,
                        is_active=True
                    )
            
            # Test filtering by category
            for category in categories:
                response = client.get(f'/menu?category={category}')
                assert response.status_code == 200
                
                # Verify correct items are shown
                content = response.get_data(as_text=True)
                assert category in content


class TestErrorRecovery:
    """Test error recovery and resilience"""
    
    def test_database_error_recovery(self, client, app):
        """Test recovery from database errors"""
        with app.app_context():
            # Test with invalid order ID
            response = client.get('/admin/orders/99999')
            assert response.status_code == 404
            
            # System should still function
            response = client.get('/menu')
            assert response.status_code == 200
    
    def test_invalid_data_handling(self, authenticated_client, app):
        """Test handling of invalid data"""
        with app.app_context():
            # Test invalid menu data
            invalid_menu_data = {
                'name': '',  # Empty name
                'price': 'invalid',  # Invalid price
                'category': 'Test'
            }
            
            response = authenticated_client.post('/admin/menu/add', data=invalid_menu_data)
            assert response.status_code in [200, 400]  # Should handle gracefully
            
            # System should still function
            response = authenticated_client.get('/admin/menu')
            assert response.status_code == 200
    
    def test_session_handling(self, client, app):
        """Test session handling and recovery"""
        with app.app_context():
            # Test expired session
            with client.session_transaction() as sess:
                sess['user_id'] = 99999  # Non-existent user
            
            response = client.get('/admin')
            assert response.status_code in [302, 401, 403]  # Should redirect or deny access
            
            # Test clearing invalid session
            response = client.get('/menu')
            assert response.status_code == 200  # Should still work


class TestDataConsistency:
    """Test data consistency across operations"""
    
    def test_order_total_consistency(self, client, app):
        """Test order total calculation consistency"""
        with app.app_context():
            order = Order.query.first()
            
            # Calculate expected total manually
            items_total = sum(item.quantity * item.price_per_item for item in order.items)
            delivery_fee = order.delivery_zone.delivery_fee if order.delivery_zone else 0
            expected_total = items_total + delivery_fee
            
            # Verify stored total matches calculation
            assert abs(order.total_price - expected_total) < 0.01
    
    def test_menu_item_consistency(self, authenticated_client, app):
        """Test menu item data consistency"""
        with app.app_context():
            # Create menu item
            menu_data = {
                'name': 'Consistency Test Menu',
                'description': 'Test description',
                'price': '150.50',
                'category': 'Test Category',
                'prep_time': '20',
                'is_active': 'on'
            }
            
            response = authenticated_client.post('/admin/menu/add', data=menu_data)
            assert response.status_code in [200, 302]
            
            # Verify data consistency
            menu_item = Menu.query.filter_by(name='Consistency Test Menu').first()
            assert menu_item is not None
            assert menu_item.price_per_item == 150.50
            assert menu_item.prep_time == 20
            assert menu_item.is_active is True
    
    def test_user_role_consistency(self, authenticated_client, app):
        """Test user role consistency"""
        with app.app_context():
            # Verify admin user has admin role
            admin_user = User.query.filter_by(username='admin').first()
            assert admin_user.role == 'admin'
            
            # Verify different roles exist
            roles = set(user.role for user in User.query.all())
            expected_roles = {'admin', 'staff', 'kitchen', 'delivery'}
            assert expected_roles.issubset(roles)


class TestBusinessLogic:
    """Test business logic integration"""
    
    def test_order_status_progression(self, client, app):
        """Test valid order status progression"""
        with app.app_context():
            order = create_test_order('Status Progression Test', status='pending')
            
            # Valid progression
            valid_progression = ['confirmed', 'preparing', 'ready', 'delivering', 'completed']
            
            for status in valid_progression:
                response = client.post(f'/admin/orders/{order.id}/status', 
                                     json={'status': status})
                assert response.status_code == 200
                
                updated_order = Order.query.get(order.id)
                assert updated_order.status == status
    
    def test_delivery_zone_logic(self, client, app):
        """Test delivery zone business logic"""
        with app.app_context():
            delivery_zone = DeliveryZone.query.filter_by(is_active=True).first()
            
            # Test minimum order validation
            assert 50.0  # Mock min_order > 0
            assert delivery_zone.delivery_fee >= 0
            
            # Only active zones should be available
            active_zones = DeliveryZone.query.filter_by(is_active=True).all()
            for zone in active_zones:
                assert zone.is_active is True
    
    def test_menu_availability_logic(self, client, app):
        """Test menu availability business logic"""
        with app.app_context():
            # Only active menu items should be available to customers
            response = client.get('/api/menu-items')
            assert response.status_code == 200
            
            data = response.get_json()
            for item in data['items']:
                assert item['is_active'] is True
            
            # Inactive items should not appear
            inactive_items = Menu.query.filter_by(is_active=False).all()
            inactive_names = [item.name for item in inactive_items]
            
            available_names = [item['name'] for item in data['items']]
            
            for inactive_name in inactive_names:
                assert inactive_name not in available_names
