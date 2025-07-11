"""
Enhanced Order System - Phase 2
Complete order processing with status tracking, notifications, and validation
"""

from flask import Blueprint, request, jsonify, session
from models import (
    db, Order, OrderItem, OrderItemOption, Menu, MenuOptionItem, 
    DeliveryZone, User, get_thai_now
)
from datetime import datetime, timedelta
import uuid
import hashlib
from cart_system import CartManager

# Create order blueprint
order_bp = Blueprint('order', __name__, url_prefix='/api/order')

class OrderManager:
    """Enhanced order management system"""
    
    ORDER_STATUSES = {
        'pending': 'รอยืนยัน',
        'confirmed': 'ยืนยันแล้ว',
        'preparing': 'กำลังเตรียม',
        'ready': 'พร้อมส่ง',
        'delivering': 'กำลังจัดส่ง',
        'delivered': 'จัดส่งแล้ว',
        'cancelled': 'ยกเลิก'
    }
    
    PAYMENT_METHODS = {
        'cod': 'เก็บเงินปลายทาง',
        'bank_transfer': 'โอนเงิน',
        'credit_card': 'บัตรเครดิต',
        'digital_wallet': 'กระเป๋าเงินดิจิทัล'
    }
    
    @staticmethod
    def generate_order_number():
        """Generate unique order number"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = str(uuid.uuid4())[:6].upper()
        return f"LAN{timestamp}{random_suffix}"
    
    @staticmethod
    def validate_customer_info(customer_data):
        """Validate customer information"""
        required_fields = ['name', 'phone', 'address']
        
        for field in required_fields:
            if not customer_data.get(field, '').strip():
                return f"Customer {field} is required"
        
        # Validate phone number format
        phone = customer_data['phone'].strip()
        if not phone.replace('-', '').replace(' ', '').isdigit():
            return "Invalid phone number format"
        
        if len(phone.replace('-', '').replace(' ', '')) < 9:
            return "Phone number too short"
        
        return None
    
    @staticmethod
    def validate_payment_info(payment_data):
        """Validate payment information"""
        method = payment_data.get('method')
        
        if method not in OrderManager.PAYMENT_METHODS:
            return "Invalid payment method"
        
        if method == 'bank_transfer':
            if not payment_data.get('transfer_slip'):
                return "Transfer slip is required for bank transfer"
        
        return None
    
    @staticmethod
    def calculate_order_totals(cart_items, delivery_fee=0, discount=0):
        """Calculate order totals with tax and fees"""
        subtotal = sum(item['total_price'] for item in cart_items)
        
        # Calculate tax (7% VAT)
        tax_rate = 0.07
        tax_amount = subtotal * tax_rate
        
        # Calculate service charge (10% for dine-in, 5% for delivery)
        service_charge_rate = 0.05  # Delivery
        service_charge = subtotal * service_charge_rate
        
        # Calculate total
        total_before_discount = subtotal + tax_amount + service_charge + delivery_fee
        discount_amount = min(discount, total_before_discount)
        final_total = total_before_discount - discount_amount
        
        return {
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax_amount, 2),
            'service_charge': round(service_charge, 2),
            'delivery_fee': round(delivery_fee, 2),
            'discount_amount': round(discount_amount, 2),
            'total': round(final_total, 2)
        }
    
    @staticmethod
    def create_order_items(order, cart_items):
        """Create order items from cart items"""
        for cart_item in cart_items:
            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                menu_id=cart_item['menu_id'],
                quantity=cart_item['quantity'],
                unit_price=cart_item['menu_price'],
                total_price=cart_item['total_price'],
                special_instructions=cart_item.get('special_instructions', '')
            )
            
            db.session.add(order_item)
            db.session.flush()  # Get order_item.id
            
            # Create order item options
            for option in cart_item.get('options', []):
                order_option = OrderItemOption(
                    order_item_id=order_item.id,
                    option_item_id=option['id'],
                    additional_price=option['price']
                )
                db.session.add(order_option)
    
    @staticmethod
    def send_order_notification(order, notification_type='new_order'):
        """Send order notification (placeholder for real implementation)"""
        # In real implementation, this would send notifications via:
        # - WebSocket to kitchen staff
        # - SMS to customer
        # - Email confirmation
        # - Push notifications to delivery staff
        
        notifications = {
            'new_order': f"New order {order.order_number} received",
            'status_update': f"Order {order.order_number} status updated to {order.status}",
            'ready_for_delivery': f"Order {order.order_number} ready for delivery",
            'delivered': f"Order {order.order_number} has been delivered"
        }
        
        print(f"[NOTIFICATION] {notifications.get(notification_type, 'Unknown notification')}")
        return True

@order_bp.route('/place', methods=['POST'])
def place_order():
    """Place a new order"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No order data provided'}), 400
        
        # Get cart from session
        cart = CartManager.get_cart()
        
        if not cart['items']:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Validate customer information
        customer_info = data.get('customer', {})
        customer_error = OrderManager.validate_customer_info(customer_info)
        if customer_error:
            return jsonify({'error': customer_error}), 400
        
        # Validate payment information
        payment_info = data.get('payment', {})
        payment_error = OrderManager.validate_payment_info(payment_info)
        if payment_error:
            return jsonify({'error': payment_error}), 400
        
        # Validate delivery zone
        delivery_zone = None
        if cart.get('zone_id'):
            delivery_zone = db.session.get(DeliveryZone, cart['zone_id'])
            if not delivery_zone or not delivery_zone.is_active:
                return jsonify({'error': 'Invalid delivery zone'}), 400
        
        # Calculate order totals
        delivery_fee = delivery_zone.delivery_fee if delivery_zone else 0
        discount = data.get('discount', 0)
        totals = OrderManager.calculate_order_totals(cart['items'], delivery_fee, discount)
        
        # Create order
        order = Order(
            order_number=OrderManager.generate_order_number(),
            customer_name=customer_info['name'].strip(),
            customer_phone=customer_info['phone'].strip(),
            customer_email=customer_info.get('email', '').strip(),
            delivery_address=customer_info['address'].strip(),
            delivery_zone_id=cart.get('zone_id'),
            order_type='delivery' if delivery_zone else 'pickup',
            payment_method=payment_info['method'],
            payment_status='pending',
            status='pending',
            subtotal=totals['subtotal'],
            tax_amount=totals['tax_amount'],
            service_charge=totals['service_charge'],
            delivery_fee=totals['delivery_fee'],
            discount_amount=totals['discount_amount'],
            total_amount=totals['total'],
            special_instructions=data.get('special_instructions', ''),
            estimated_delivery_time=get_thai_now() + timedelta(minutes=45),  # Default 45 min
            created_at=get_thai_now()
        )
        
        db.session.add(order)
        db.session.flush()  # Get order.id
        
        # Create order items
        OrderManager.create_order_items(order, cart['items'])
        
        # Commit transaction
        db.session.commit()
        
        # Clear cart
        session['cart'] = {
            'items': [],
            'zone_id': None,
            'subtotal': 0,
            'delivery_fee': 0,
            'total': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Send notification
        OrderManager.send_order_notification(order, 'new_order')
        
        return jsonify({
            'success': True,
            'message': 'Order placed successfully',
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'status_text': OrderManager.ORDER_STATUSES.get(order.status),
                'total_amount': float(order.total_amount),
                'estimated_delivery_time': order.estimated_delivery_time.isoformat(),
                'payment_method': order.payment_method,
                'payment_method_text': OrderManager.PAYMENT_METHODS.get(order.payment_method)
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to place order: {str(e)}'}), 500

@order_bp.route('/<order_number>/status', methods=['GET'])
def get_order_status(order_number):
    """Get order status and details"""
    try:
        order = Order.query.filter_by(order_number=order_number).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get order items with details
        order_items = []
        for item in order.items:
            menu = db.session.get(Menu, item.menu_id)
            
            # Get options
            options = []
            for option in item.options:
                option_item = db.session.get(MenuOptionItem, option.option_item_id)
                if option_item:
                    options.append({
                        'name': option_item.name,
                        'price': float(option.additional_price)
                    })
            
            order_items.append({
                'menu_name': menu.name if menu else 'Unknown Item',
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price),
                'options': options,
                'special_instructions': item.special_instructions
            })
        
        # Calculate estimated times
        current_time = get_thai_now()
        time_remaining = None
        if order.estimated_delivery_time and order.status not in ['delivered', 'cancelled']:
            time_remaining = max(0, int((order.estimated_delivery_time - current_time).total_seconds() / 60))
        
        return jsonify({
            'success': True,
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'status_text': OrderManager.ORDER_STATUSES.get(order.status),
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'delivery_address': order.delivery_address,
                'order_type': order.order_type,
                'payment_method': order.payment_method,
                'payment_method_text': OrderManager.PAYMENT_METHODS.get(order.payment_method),
                'payment_status': order.payment_status,
                'subtotal': float(order.subtotal),
                'tax_amount': float(order.tax_amount),
                'service_charge': float(order.service_charge),
                'delivery_fee': float(order.delivery_fee),
                'discount_amount': float(order.discount_amount),
                'total_amount': float(order.total_amount),
                'estimated_delivery_time': order.estimated_delivery_time.isoformat() if order.estimated_delivery_time else None,
                'time_remaining_minutes': time_remaining,
                'created_at': order.created_at.isoformat(),
                'items': order_items,
                'special_instructions': order.special_instructions
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get order status: {str(e)}'}), 500

@order_bp.route('/<order_number>/cancel', methods=['POST'])
def cancel_order(order_number):
    """Cancel an order (if allowed)"""
    try:
        order = Order.query.filter_by(order_number=order_number).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check if order can be cancelled
        if order.status in ['delivered', 'cancelled']:
            return jsonify({'error': 'Order cannot be cancelled'}), 400
        
        if order.status in ['ready', 'delivering']:
            return jsonify({'error': 'Order is too far along to cancel'}), 400
        
        # Cancel order
        order.status = 'cancelled'
        order.updated_at = get_thai_now()
        
        db.session.commit()
        
        # Send notification
        OrderManager.send_order_notification(order, 'status_update')
        
        return jsonify({
            'success': True,
            'message': 'Order cancelled successfully',
            'order': {
                'order_number': order.order_number,
                'status': order.status,
                'status_text': OrderManager.ORDER_STATUSES.get(order.status)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to cancel order: {str(e)}'}), 500

@order_bp.route('/customer/<phone>', methods=['GET'])
def get_customer_orders(phone):
    """Get all orders for a customer by phone number"""
    try:
        # Validate phone number
        if not phone or len(phone.replace('-', '').replace(' ', '')) < 9:
            return jsonify({'error': 'Invalid phone number'}), 400
        
        # Get orders
        orders = Order.query.filter_by(customer_phone=phone).order_by(Order.created_at.desc()).limit(20).all()
        
        order_list = []
        for order in orders:
            order_list.append({
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'status_text': OrderManager.ORDER_STATUSES.get(order.status),
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.isoformat(),
                'estimated_delivery_time': order.estimated_delivery_time.isoformat() if order.estimated_delivery_time else None
            })
        
        return jsonify({
            'success': True,
            'orders': order_list,
            'total_orders': len(order_list)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get customer orders: {str(e)}'}), 500
