"""
LanAim POS System v2.4 - Phase 1
API Routes Blueprint

This module handles all API endpoints for:
- Order management (CRUD operations)
- Cart operations
- Real-time status updates
- Feedback submission
"""

from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from models import db, Order, OrderItem, OrderItemOption, Menu, MenuOptionItem, Feedback, DeliveryZone
from routes.customer import add_to_cart, remove_from_cart, update_cart_quantity, clear_cart
from routes.staff import can_update_order_status
from datetime import datetime
import re

# Create API blueprint
api_bp = Blueprint('api', __name__)

# ==================== CART API ENDPOINTS ====================

@api_bp.route('/cart/add', methods=['POST'])
def add_cart_item():
    """
    Add item to cart
    
    Expected JSON:
    {
        "menu_id": int,
        "quantity": int,
        "options": [int, ...],  # Optional
        "special_requests": str  # Optional
    }
    """
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'ไม่มีข้อมูล'}), 400
        
        menu_id = data.get('menu_id')
        quantity = data.get('quantity', 1)
        options = data.get('options', [])
        special_requests = data.get('special_requests')
        
        # Validate required fields
        if not menu_id or quantity <= 0:
            return jsonify({'error': 'ข้อมูลไม่ถูกต้อง'}), 400
        
        # Add to cart
        success = add_to_cart(menu_id, quantity, options, special_requests)
        
        if success:
            cart_count = len(session.get('cart', []))
            return jsonify({
                'success': True,
                'message': 'เพิ่มลงตะกร้าเรียบร้อยแล้ว',
                'cart_count': cart_count
            })
        else:
            return jsonify({'error': 'ไม่สามารถเพิ่มสินค้าได้'}), 400
            
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดภายในระบบ'}), 500

@api_bp.route('/cart/remove', methods=['POST'])
def remove_cart_item():
    """
    Remove item from cart
    
    Expected JSON:
    {
        "cart_item_id": str
    }
    """
    
    try:
        data = request.get_json()
        cart_item_id = data.get('cart_item_id')
        
        if not cart_item_id:
            return jsonify({'error': 'ไม่มีรหัสสินค้า'}), 400
        
        remove_from_cart(cart_item_id)
        
        cart_count = len(session.get('cart', []))
        return jsonify({
            'success': True,
            'message': 'ลบสินค้าเรียบร้อยแล้ว',
            'cart_count': cart_count
        })
        
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดภายในระบบ'}), 500

@api_bp.route('/cart/update', methods=['POST'])
def update_cart_item():
    """
    Update cart item quantity
    
    Expected JSON:
    {
        "cart_item_id": str,
        "quantity": int
    }
    """
    
    try:
        data = request.get_json()
        cart_item_id = data.get('cart_item_id')
        quantity = data.get('quantity', 1)
        
        if not cart_item_id or quantity < 0:
            return jsonify({'error': 'ข้อมูลไม่ถูกต้อง'}), 400
        
        update_cart_quantity(cart_item_id, quantity)
        
        cart_count = len(session.get('cart', []))
        return jsonify({
            'success': True,
            'message': 'อัปเดตจำนวนเรียบร้อยแล้ว',
            'cart_count': cart_count
        })
        
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดภายในระบบ'}), 500

@api_bp.route('/cart/clear', methods=['POST'])
def clear_cart_api():
    """Clear all items from cart"""
    
    try:
        clear_cart()
        return jsonify({
            'success': True,
            'message': 'ล้างตะกร้าเรียบร้อยแล้ว'
        })
        
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดภายในระบบ'}), 500

# ==================== ORDER API ENDPOINTS ====================

@api_bp.route('/order', methods=['POST'])
def create_order():
    """
    Create new order from cart
    
    Expected JSON:
    {
        "customer_name": str,
        "customer_phone": str,
        "delivery_address": str,
        "delivery_zone_id": int,  # Optional
        "payment_method": str  # "COD" or "TOD"
    }
    """
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'ไม่มีข้อมูล'}), 400
        
        # Validate required fields
        required_fields = ['customer_name', 'customer_phone', 'delivery_address', 'payment_method']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'กรุณากรอก{field}'}), 400
        
        # Validate phone number (basic Thai phone number validation)
        phone = data['customer_phone']
        if not re.match(r'^[0-9]{9,10}$', phone):
            return jsonify({'error': 'เบอร์โทรศัพท์ไม่ถูกต้อง'}), 400
        
        # Validate payment method
        if data['payment_method'] not in ['COD', 'TOD']:
            return jsonify({'error': 'วิธีการชำระเงินไม่ถูกต้อง'}), 400
        
        # Get cart from session
        cart_items = session.get('cart', [])
        if not cart_items:
            return jsonify({'error': 'ตะกร้าสินค้าว่างเปล่า'}), 400
        
        # Calculate total price
        total_price = sum(item['total_price'] for item in cart_items)
        
        # Create order
        order = Order(
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            delivery_address_details=data['delivery_address'],
            delivery_zone_id=data.get('delivery_zone_id'),
            total_price=total_price,
            payment_method=data['payment_method']
        )
        
        # Generate order number
        order.generate_order_number()
        
        # Save order to get ID
        db.session.add(order)
        db.session.flush()
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                menu_id=cart_item['menu_id'],
                menu_name=cart_item['menu_name'],
                price_per_item=cart_item['base_price'],
                quantity=cart_item['quantity'],
                special_requests=cart_item.get('special_requests')
            )
            
            db.session.add(order_item)
            db.session.flush()
            
            # Add order item options
            for option in cart_item['options']:
                order_option = OrderItemOption(
                    order_item_id=order_item.id,
                    option_id=option['id'],
                    option_name=option['name'],
                    option_price=option['price']
                )
                db.session.add(order_option)
        
        # Commit the transaction
        db.session.commit()
        
        # Clear cart after successful order
        clear_cart()
        
        # Emit real-time notification to staff (will be implemented with SocketIO)
        emit_new_order_notification(order)
        
        return jsonify({
            'success': True,
            'message': 'สั่งอาหารเรียบร้อยแล้ว',
            'order_number': order.order_number,
            'order_id': order.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'เกิดข้อผิดพลาดในการสั่งอาหาร'}), 500

@api_bp.route('/order/<order_number>/status', methods=['GET'])
def get_order_status(order_number):
    """
    Get current order status
    
    Args:
        order_number (str): Order number to check
    """
    
    try:
        order = Order.query.filter_by(order_number=order_number).first()
        
        if not order:
            return jsonify({'error': 'ไม่พบออเดอร์'}), 404
        
        return jsonify({
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'total_price': float(order.total_price),
            'payment_method': order.payment_method,
            'payment_status': order.payment_status,
            'created_at': order.created_at.isoformat(),
            'last_updated_at': order.last_updated_at.isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดในการดึงข้อมูล'}), 500

@api_bp.route('/order/<int:order_id>/status', methods=['PATCH'])
@login_required
def update_order_status(order_id):
    """
    Update order status (staff only)
    
    Expected JSON:
    {
        "status": str
    }
    
    Args:
        order_id (int): Order ID to update
    """
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'ไม่มีสถานะใหม่'}), 400
        
        order = Order.query.get_or_404(order_id)
        
        # Check if user can update to this status
        if not can_update_order_status(order, current_user, new_status):
            return jsonify({'error': 'ไม่สามารถเปลี่ยนสถานะได้'}), 403
        
        # Update order status
        order.update_status(new_status, current_user)
        db.session.commit()
        
        # Emit real-time notification
        emit_order_status_update(order)
        
        return jsonify({
            'success': True,
            'message': f'เปลี่ยนสถานะเป็น {order.get_status_display()} เรียบร้อยแล้ว',
            'order_id': order.id,
            'new_status': order.status,
            'status_display': order.get_status_display()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'เกิดข้อผิดพลาดในการอัปเดตสถานะ'}), 500

@api_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """
    Cancel order (customer or staff)
    
    Args:
        order_id (int): Order ID to cancel
    """
    
    try:
        order = Order.query.get_or_404(order_id)
        
        # Check if order can be cancelled
        if not order.can_be_cancelled():
            return jsonify({'error': 'ไม่สามารถยกเลิกออเดอร์ได้'}), 400
        
        # Update status to cancelled
        order.update_status('cancelled', current_user if current_user.is_authenticated else None)
        db.session.commit()
        
        # Emit real-time notification
        emit_order_status_update(order)
        
        return jsonify({
            'success': True,
            'message': 'ยกเลิกออเดอร์เรียบร้อยแล้ว',
            'order_id': order.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'เกิดข้อผิดพลาดในการยกเลิกออเดอร์'}), 500

@api_bp.route('/order/<order_number>/details', methods=['GET'])
def get_order_details(order_number):
    """
    Get detailed order information including items and options
    
    Args:
        order_number (str): Order number to get details for
    """
    
    try:
        order = Order.query.filter_by(order_number=order_number).first()
        
        if not order:
            return jsonify({'error': 'ไม่พบออเดอร์'}), 404
        
        # Build items list with details
        items_data = []
        for item in order.items:
            item_data = {
                'id': item.id,
                'menu_name': item.menu_name,
                'quantity': item.quantity,
                'unit_price': float(item.price_per_item),
                'subtotal': float(item.get_total_price()),
                'special_instructions': item.special_requests,
                'options': []
            }
            
            # Add selected options
            for option in item.options:
                item_data['options'].append({
                    'name': option.option_name,
                    'additional_price': float(option.option_price)
                })
            
            items_data.append(item_data)
        
        # Build response
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'delivery_address_details': order.delivery_address_details,
            'total_price': float(order.total_price),
            'status': order.status,
            'status_display': order.get_status_display(),
            'payment_method': order.payment_method,
            'payment_status': order.payment_status,
            'created_at': order.created_at.isoformat(),
            'last_updated_at': order.last_updated_at.isoformat() if order.last_updated_at else None,
            'zone': {
                'id': order.delivery_zone.id,
                'name': order.delivery_zone.name
            } if order.delivery_zone else None,
            'items': items_data
        }
        
        return jsonify(order_data)
        
    except Exception as e:
        print(f"Error in get_order_details: {str(e)}")  # Debug print
        import traceback
        traceback.print_exc()  # Print full traceback
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

# ==================== FEEDBACK API ENDPOINTS ====================

@api_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """
    Submit customer feedback
    
    Expected JSON:
    {
        "order_id": int,
        "rating": int,  # 1-5
        "comment": str  # Optional
    }
    """
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'ไม่มีข้อมูล'}), 400
        
        order_id = data.get('order_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        # Validate required fields
        if not order_id or not rating:
            return jsonify({'error': 'กรุณากรอกข้อมูลให้ครบถ้วน'}), 400
        
        # Validate rating range
        if rating < 1 or rating > 5:
            return jsonify({'error': 'คะแนนต้องอยู่ระหว่าง 1-5'}), 400
        
        # Check if order exists and is completed
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'error': 'ไม่พบออเดอร์'}), 404
        
        if order.status != 'completed':
            return jsonify({'error': 'ไม่สามารถให้ความคิดเห็นได้ในขณะนี้'}), 400
        
        # Check if feedback already exists
        existing_feedback = Feedback.query.filter_by(order_id=order_id).first()
        if existing_feedback:
            return jsonify({'error': 'ได้ให้ความคิดเห็นแล้ว'}), 400
        
        # Create feedback
        feedback = Feedback(
            order_id=order_id,
            rating=rating,
            comment=comment
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'ขอบคุณสำหรับความคิดเห็น'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'เกิดข้อผิดพลาดในการส่งความคิดเห็น'}), 500

# ==================== UTILITY FUNCTIONS ====================

def emit_new_order_notification(order):
    """
    Emit real-time notification for new order
    (Will be implemented with SocketIO in real-time features)
    
    Args:
        order (Order): New order object
    """
    # TODO: Implement SocketIO emission
    pass

def emit_order_status_update(order):
    """
    Emit real-time notification for order status update
    (Will be implemented with SocketIO in real-time features)
    
    Args:
        order (Order): Updated order object
    """
    # TODO: Implement SocketIO emission
    pass

# ==================== HELPER API ENDPOINTS ====================

@api_bp.route('/zones', methods=['GET'])
def get_zones():
    """Get all active delivery zones"""
    
    try:
        zones = DeliveryZone.query.filter_by(is_active=True).all()
        
        zones_data = []
        for zone in zones:
            zones_data.append({
                'id': zone.id,
                'name': zone.name,
                'description': zone.description
            })
        
        return jsonify({
            'success': True,
            'zones': zones_data
        })
        
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดในการดึงข้อมูลโซน'}), 500

@api_bp.route('/menu', methods=['GET'])
def get_menu():
    """Get all active menu items"""
    
    try:
        menus = Menu.query.filter_by(is_active=True).all()
        
        menu_data = []
        for menu in menus:
            menu_item = {
                'id': menu.id,
                'name': menu.name,
                'description': menu.description,
                'price': float(menu.price),
                'category': menu.category,
                'image_url': menu.image_url
            }
            menu_data.append(menu_item)
        
        return jsonify({
            'success': True,
            'menu': menu_data
        })
        
    except Exception as e:
        return jsonify({'error': 'เกิดข้อผิดพลาดในการดึงข้อมูลเมนู'}), 500
