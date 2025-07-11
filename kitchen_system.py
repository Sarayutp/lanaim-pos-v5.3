"""
Kitchen Interface System - Phase 2
Real-time order management for kitchen staff with status tracking
"""

from flask import Blueprint, render_template, request, jsonify
from models import db, Order, OrderItem, Menu, User, get_thai_now
from datetime import datetime, timedelta
from routes.staff import staff_required
from order_system import OrderManager

# Create kitchen blueprint
kitchen_bp = Blueprint('kitchen', __name__, url_prefix='/kitchen')

class KitchenManager:
    """Kitchen operation management"""
    
    KITCHEN_STATUSES = {
        'pending': {'text': 'รอยืนยัน', 'color': 'yellow', 'priority': 1},
        'confirmed': {'text': 'ยืนยันแล้ว', 'color': 'blue', 'priority': 2},
        'preparing': {'text': 'กำลังเตรียม', 'color': 'orange', 'priority': 3},
        'ready': {'text': 'พร้อมส่ง', 'color': 'green', 'priority': 4},
        'delivering': {'text': 'กำลังจัดส่ง', 'color': 'purple', 'priority': 5},
        'delivered': {'text': 'จัดส่งแล้ว', 'color': 'gray', 'priority': 6},
        'cancelled': {'text': 'ยกเลิก', 'color': 'red', 'priority': 0}
    }
    
    @staticmethod
    def get_active_orders():
        """Get orders that need kitchen attention"""
        return Order.query.filter(
            Order.status.in_(['pending', 'confirmed', 'preparing'])
        ).order_by(Order.created_at.asc()).all()
    
    @staticmethod
    def get_ready_orders():
        """Get orders ready for delivery"""
        return Order.query.filter(
            Order.status == 'ready'
        ).order_by(Order.created_at.asc()).all()
    
    @staticmethod
    def calculate_order_timing(order):
        """Calculate timing information for order"""
        current_time = get_thai_now()
        
        # Time since order was placed
        time_elapsed = int((current_time - order.created_at).total_seconds() / 60)
        
        # Estimated prep time based on items
        estimated_prep = 0
        for item in order.items:
            menu = db.session.get(Menu, item.menu_id)
            if menu and menu.prep_time:
                item_prep = menu.prep_time * item.quantity
                estimated_prep = max(estimated_prep, item_prep)
        
        # Add buffer time
        estimated_prep += 10
        
        # Calculate remaining time
        time_remaining = max(0, estimated_prep - time_elapsed)
        
        # Determine urgency
        urgency = 'normal'
        if time_elapsed > estimated_prep + 10:
            urgency = 'overdue'
        elif time_elapsed > estimated_prep - 5:
            urgency = 'urgent'
        
        return {
            'time_elapsed': time_elapsed,
            'estimated_prep': estimated_prep,
            'time_remaining': time_remaining,
            'urgency': urgency
        }
    
    @staticmethod
    def get_kitchen_stats():
        """Get kitchen performance statistics"""
        today = get_thai_now().date()
        
        # Today's orders
        today_orders = Order.query.filter(
            db.func.date(Order.created_at) == today
        ).all()
        
        # Calculate stats
        total_orders = len(today_orders)
        completed_orders = len([o for o in today_orders if o.status in ['delivered']])
        pending_orders = len([o for o in today_orders if o.status in ['pending', 'confirmed', 'preparing']])
        cancelled_orders = len([o for o in today_orders if o.status == 'cancelled'])
        
        # Average prep time for completed orders
        avg_prep_time = 0
        if completed_orders > 0:
            total_prep_time = 0
            for order in today_orders:
                if order.status == 'delivered':
                    # Calculate actual prep time (from created to ready)
                    # This would be more accurate with proper status timestamps
                    timing = KitchenManager.calculate_order_timing(order)
                    total_prep_time += timing['estimated_prep']
            avg_prep_time = int(total_prep_time / completed_orders)
        
        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'pending_orders': pending_orders,
            'cancelled_orders': cancelled_orders,
            'avg_prep_time': avg_prep_time,
            'completion_rate': round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 1)
        }

@kitchen_bp.route('/')
@staff_required
def kitchen_dashboard():
    """Kitchen dashboard main page"""
    try:
        # Get orders
        active_orders = KitchenManager.get_active_orders()
        ready_orders = KitchenManager.get_ready_orders()
        
        # Enhance orders with timing info
        enhanced_active = []
        for order in active_orders:
            timing = KitchenManager.calculate_order_timing(order)
            status_info = KitchenManager.KITCHEN_STATUSES.get(order.status, {})
            
            enhanced_active.append({
                'order': order,
                'timing': timing,
                'status_info': status_info,
                'items_summary': ', '.join([f"{item.quantity}x {db.session.get(Menu, item.menu_id).name if db.session.get(Menu, item.menu_id) else 'Unknown'}" for item in order.items])
            })
        
        enhanced_ready = []
        for order in ready_orders:
            timing = KitchenManager.calculate_order_timing(order)
            status_info = KitchenManager.KITCHEN_STATUSES.get(order.status, {})
            
            enhanced_ready.append({
                'order': order,
                'timing': timing,
                'status_info': status_info,
                'items_summary': ', '.join([f"{item.quantity}x {db.session.get(Menu, item.menu_id).name if db.session.get(Menu, item.menu_id) else 'Unknown'}" for item in order.items])
            })
        
        # Get kitchen stats
        stats = KitchenManager.get_kitchen_stats()
        
        return render_template('kitchen/dashboard.html',
                             active_orders=enhanced_active,
                             ready_orders=enhanced_ready,
                             stats=stats,
                             current_time=get_thai_now())
        
    except Exception as e:
        return f"Error loading kitchen dashboard: {str(e)}", 500

@kitchen_bp.route('/order/<int:order_id>')
@staff_required
def order_details(order_id):
    """Detailed view of specific order"""
    try:
        order = db.session.get(Order, order_id)
        
        if not order:
            return "Order not found", 404
        
        # Get detailed items
        detailed_items = []
        for item in order.items:
            menu = db.session.get(Menu, item.menu_id)
            
            # Get options
            options = []
            for option in item.options:
                from models import MenuOptionItem
                option_item = db.session.get(MenuOptionItem, option.option_item_id)
                if option_item:
                    options.append({
                        'name': option_item.name,
                        'price': float(option.additional_price)
                    })
            
            detailed_items.append({
                'item': item,
                'menu': menu,
                'options': options
            })
        
        # Get timing info
        timing = KitchenManager.calculate_order_timing(order)
        status_info = KitchenManager.KITCHEN_STATUSES.get(order.status, {})
        
        return render_template('kitchen/order_details.html',
                             order=order,
                             detailed_items=detailed_items,
                             timing=timing,
                             status_info=status_info)
        
    except Exception as e:
        return f"Error loading order details: {str(e)}", 500

@kitchen_bp.route('/api/order/<int:order_id>/status', methods=['PUT'])
@staff_required
def update_order_status(order_id):
    """Update order status from kitchen"""
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        new_status = data['status']
        
        if new_status not in KitchenManager.KITCHEN_STATUSES:
            return jsonify({'error': 'Invalid status'}), 400
        
        order = db.session.get(Order, order_id)
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Validate status transition
        current_status = order.status
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready', 'cancelled'],
            'ready': ['delivering'],
            'delivering': ['delivered'],
            'delivered': [],
            'cancelled': []
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            return jsonify({'error': f'Cannot change status from {current_status} to {new_status}'}), 400
        
        # Update status
        order.status = new_status
        order.updated_at = get_thai_now()
        
        # Set specific timestamps
        if new_status == 'confirmed':
            order.confirmed_at = get_thai_now()
        elif new_status == 'preparing':
            order.preparation_started_at = get_thai_now()
        elif new_status == 'ready':
            order.ready_at = get_thai_now()
            # Update estimated delivery time
            order.estimated_delivery_time = get_thai_now() + timedelta(minutes=20)
        elif new_status == 'delivering':
            order.delivery_started_at = get_thai_now()
        elif new_status == 'delivered':
            order.delivered_at = get_thai_now()
        
        db.session.commit()
        
        # Send notification
        OrderManager.send_order_notification(order, 'status_update')
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {KitchenManager.KITCHEN_STATUSES[new_status]["text"]}',
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'status_text': KitchenManager.KITCHEN_STATUSES[new_status]['text']
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update order status: {str(e)}'}), 500

@kitchen_bp.route('/api/orders/active')
@staff_required
def get_active_orders_api():
    """API endpoint for active orders (for real-time updates)"""
    try:
        active_orders = KitchenManager.get_active_orders()
        
        orders_data = []
        for order in active_orders:
            timing = KitchenManager.calculate_order_timing(order)
            status_info = KitchenManager.KITCHEN_STATUSES.get(order.status, {})
            
            # Get items summary
            items = []
            for item in order.items:
                menu = db.session.get(Menu, item.menu_id)
                items.append({
                    'name': menu.name if menu else 'Unknown',
                    'quantity': item.quantity,
                    'special_instructions': item.special_instructions
                })
            
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'status': order.status,
                'status_info': status_info,
                'timing': timing,
                'items': items,
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'stats': KitchenManager.get_kitchen_stats()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get active orders: {str(e)}'}), 500

@kitchen_bp.route('/api/stats')
@staff_required  
def get_kitchen_stats_api():
    """API endpoint for kitchen statistics"""
    try:
        stats = KitchenManager.get_kitchen_stats()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': get_thai_now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get kitchen stats: {str(e)}'}), 500
