"""
LanAim POS System v2.4 - Phase 3
Customer Routes Blueprint - Enhanced Experience

This module handles all customer-facing routes including:
- Menu browsing with enhanced customization
- Order placement with rate limiting
- Real-time order tracking
- Order modification and cancellation
- Feedback submission with improved UI
- Session management for spam prevention
"""

from flask import Blueprint, render_template, request, jsonify, session
from models import (
    db, Menu, MenuOptionGroup, MenuOptionItem, DeliveryZone, 
    Order, OrderItem, OrderItemOption, Feedback, CustomerSession,
    get_thai_now
)
import uuid
import hashlib
from datetime import datetime, timedelta

# Create customer blueprint
customer_bp = Blueprint('customer', __name__)

def get_or_create_session():
    """
    Get or create customer session for rate limiting and tracking
    """
    # Get session ID from browser session
    session_id = session.get('customer_session_id')
    
    if not session_id:
        # Create new session ID
        session_id = str(uuid.uuid4())
        session['customer_session_id'] = session_id
    
    # Get or create customer session record
    customer_session = CustomerSession.query.filter_by(session_id=session_id).first()
    
    if not customer_session:
        customer_session = CustomerSession(
            session_id=session_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(customer_session)
        db.session.commit()
    else:
        # Update last activity
        customer_session.last_activity = get_thai_now()
        db.session.commit()
    
    return customer_session

def check_rate_limit():
    """
    Check if current session can place orders (rate limiting)
    Returns: (can_order: bool, message: str)
    """
    customer_session = get_or_create_session()
    return customer_session.can_place_order()

@customer_bp.route('/')
def index():
    """
    Landing page - redirects to menu or shows QR code scanner
    In a real implementation, this would handle QR code scanning
    For now, we'll redirect to menu with a default zone
    """
    return render_template('customer/index.html')

@customer_bp.route('/menu')
@customer_bp.route('/menu/<int:zone_id>')
def menu(zone_id=None):
    """
    Display menu with all available items
    
    Args:
        zone_id (int): Optional zone ID from QR code scan
    """
    
    # Get zone information if provided
    zone = None
    if zone_id:
        zone = db.session.get(DeliveryZone, zone_id)
        # Store zone in session for order placement
        session['selected_zone_id'] = zone_id
    
    # Get all active menu items grouped by category
    menus = Menu.query.filter_by(is_active=True).all()
    
    # Group menus by category
    menu_categories = {}
    for menu in menus:
        category = menu.category or 'อื่นๆ'
        if category not in menu_categories:
            menu_categories[category] = []
        menu_categories[category].append(menu)
    
    # Get cart info from session
    cart_count = len(session.get('cart', []))
    
    return render_template('customer/menu.html', 
                         menu_categories=menu_categories,
                         selected_zone=zone,
                         cart_count=cart_count)

@customer_bp.route('/menu/<int:menu_id>/options')
def menu_options(menu_id):
    """
    Get menu options for customization via AJAX
    
    Args:
        menu_id (int): Menu item ID
    """
    
    menu = Menu.query.get_or_404(menu_id)
    
    # Get all active option groups for this menu
    option_groups = MenuOptionGroup.query.filter_by(menu_id=menu_id, is_active=True).all()
    
    options_data = []
    for group in option_groups:
        group_data = {
            'id': group.id,
            'name': group.name,
            'is_required': group.is_required,
            'is_multiple': group.is_multiple,
            'max_selections': group.max_selections,
            'options': []
        }
        
        for option in group.options:
            if option.is_active:
                group_data['options'].append({
                    'id': option.id,
                    'name': option.name,
                    'price': float(option.additional_price)
                })
        
        options_data.append(group_data)
    
    return jsonify({
        'menu': {
            'id': menu.id,
            'name': menu.name,
            'price': float(menu.price),
            'description': menu.description
        },
        'option_groups': options_data
    })

@customer_bp.route('/cart')
def cart():
    """Display shopping cart"""
    
    # Get cart from session
    cart_items = session.get('cart', [])
    
    # Get available zones for delivery
    zones = DeliveryZone.query.filter_by(is_active=True).all()
    
    # Calculate cart total
    cart_total = sum(item['total_price'] for item in cart_items)
    
    selected_zone_id = session.get('selected_zone_id')
    selected_zone = None
    if selected_zone_id:
        selected_zone = db.session.get(DeliveryZone, selected_zone_id)
    
    return render_template('customer/cart.html',
                         cart_items=cart_items,
                         cart_total=cart_total,
                         zones=zones,
                         selected_zone=selected_zone)

@customer_bp.route('/order/<order_number>')
def order_tracking(order_number):
    """
    Order tracking page
    
    Args:
        order_number (str): Order number to track
    """
    
    def get_progress_width(status):
        """Calculate progress bar width based on order status"""
        status_progress = {
            'pending': 0,
            'accepted': 16,       # 1/5 * 80%
            'preparing': 32,      # 2/5 * 80%
            'ready': 48,          # 3/5 * 80%
            'delivering': 64,     # 4/5 * 80%
            'delivered': 80,      # 5/5 * 80% (connect to second-to-last icon)
            'completed': 80,      # Same as delivered
            'cancelled': 0
        }
        return status_progress.get(status, 0)
    
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    
    return render_template('customer/order_tracking.html', 
                         order=order, 
                         get_progress_width=get_progress_width)

# =============================================================================
# PHASE 3 ENHANCEMENTS - Order Management
# =============================================================================

@customer_bp.route('/order/cancel/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    """
    Cancel a pending order
    Only allowed before order is accepted
    """
    try:
        order = Order.query.get_or_404(order_id)
        
        # Check if order can be cancelled
        if not order.can_be_cancelled():
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถยกเลิกออเดอร์ได้ เนื่องจากออเดอร์ได้รับการยืนยันแล้ว'
            }), 400
        
        # Update order status
        order.update_status('cancelled')
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'ยกเลิกออเดอร์เรียบร้อยแล้ว'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500


@customer_bp.route('/order/modify/<int:order_id>')
def modify_order_form(order_id):
    """
    Show order modification form
    Only allowed for pending orders
    """
    order = Order.query.get_or_404(order_id)
    
    if not order.can_be_modified():
        return render_template('customer/error.html', 
                             message='ไม่สามารถแก้ไขออเดอร์ได้ เนื่องจากออเดอร์ได้รับการยืนยันแล้ว')
    
    # Get current order items for modification
    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    
    # Convert to cart format for editing
    cart_items = []
    for item in order_items:
        # Get item options
        item_options = OrderItemOption.query.filter_by(order_item_id=item.id).all()
        options = []
        for opt in item_options:
            options.append({
                'id': opt.option_ref.id if opt.option_ref else None,
                'name': opt.option_name,
                'price': float(opt.option_price)
            })
        
        cart_items.append({
            'id': str(uuid.uuid4()),
            'menu_id': item.menu_id,
            'menu_name': item.menu_name,
            'base_price': float(item.menu.price),
            'quantity': item.quantity,
            'options': options,
            'special_requests': item.special_requests,
            'total_price': float(item.price)
        })
    
    # Store original order in session for modification
    session['modifying_order_id'] = order_id
    session['cart'] = cart_items
    
    return render_template('customer/modify_order.html', order=order, cart_items=cart_items)


@customer_bp.route('/order/update/<int:order_id>', methods=['POST'])
def update_order(order_id):
    """
    Update a pending order with new items
    """
    try:
        order = Order.query.get_or_404(order_id)
        
        if not order.can_be_modified():
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถแก้ไขออเดอร์ได้ เนื่องจากออเดอร์ได้รับการยืนยันแล้ว'
            }), 400
        
        # Check rate limiting
        can_order, message = check_rate_limit()
        if not can_order:
            return jsonify({
                'success': False,
                'message': message
            }), 429
        
        # Get new cart from session
        cart = session.get('cart', [])
        if not cart:
            return jsonify({
                'success': False,
                'message': 'ไม่มีรายการในตะกร้า'
            }), 400
        
        # Delete existing order items
        OrderItemOption.query.filter(
            OrderItemOption.order_item_id.in_(
                db.session.query(OrderItem.id).filter_by(order_id=order.id)
            )
        ).delete(synchronize_session=False)
        
        OrderItem.query.filter_by(order_id=order.id).delete()
        
        # Recreate order items from cart
        total_price = 0
        
        for cart_item in cart:
            menu = db.session.get(Menu, cart_item['menu_id'])
            if not menu or not menu.is_active:
                continue
            
            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                menu_id=menu.id,
                menu_name=menu.name,
                quantity=cart_item['quantity'],
                price=cart_item['total_price'],
                special_requests=cart_item.get('special_requests')
            )
            db.session.add(order_item)
            db.session.flush()  # Get the ID
            
            # Add options
            for option in cart_item.get('options', []):
                if option.get('id'):
                    option_item = db.session.get(MenuOptionItem, option['id'])
                    if option_item:
                        order_option = OrderItemOption(
                            order_item_id=order_item.id,
                            option_id=option_item.id,
                            option_name=option_item.name,
                            option_price=option_item.additional_price
                        )
                        db.session.add(order_option)
            
            total_price += cart_item['total_price']
        
        # Update order total
        order.total_price = total_price
        order.last_updated_at = get_thai_now()
        
        # Record session activity
        customer_session = get_or_create_session()
        customer_session.record_order()
        
        db.session.commit()
        
        # Clear cart and modification session
        session.pop('cart', None)
        session.pop('modifying_order_id', None)
        
        return jsonify({
            'success': True,
            'message': 'แก้ไขออเดอร์เรียบร้อยแล้ว',
            'order_id': order.id,
            'order_number': order.order_number,
            'total_price': float(order.total_price)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500


@customer_bp.route('/feedback/<int:order_id>')
def feedback_form(order_id):
    """
    Show feedback form for completed order
    """
    order = Order.query.get_or_404(order_id)
    
    # Check if order is completed
    if order.status not in ['delivered', 'completed']:
        return render_template('customer/error.html', 
                             message='สามารถให้คะแนนได้เฉพาะออเดอร์ที่เสร็จสิ้นแล้วเท่านั้น')
    
    # Check if feedback already exists
    existing_feedback = Feedback.query.filter_by(order_id=order.id).first()
    
    return render_template('customer/feedback.html', 
                         order=order, 
                         existing_feedback=existing_feedback)


@customer_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """
    Submit customer feedback and rating
    Enhanced with better validation and UX
    """
    try:
        data = request.get_json()
        
        order_id = data.get('order_id')
        rating = data.get('rating')
        comment = data.get('comment', '').strip()
        
        # Validation
        if not order_id or not rating:
            return jsonify({
                'success': False,
                'message': 'กรุณาระบุหมายเลขออเดอร์และคะแนน'
            }), 400
        
        if not (1 <= int(rating) <= 5):
            return jsonify({
                'success': False,
                'message': 'กรุณาให้คะแนน 1-5 ดาว'
            }), 400
        
        # Get order
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': 'ไม่พบออเดอร์ที่ระบุ'
            }), 404
        
        # Check if order is completed
        if order.status not in ['delivered', 'completed']:
            return jsonify({
                'success': False,
                'message': 'สามารถให้คะแนนได้เฉพาะออเดอร์ที่เสร็จสิ้นแล้วเท่านั้น'
            }), 400
        
        # Check if feedback already exists
        existing_feedback = Feedback.query.filter_by(order_id=order.id).first()
        
        if existing_feedback:
            # Update existing feedback
            existing_feedback.rating = int(rating)
            existing_feedback.comment = comment
            message = 'อัปเดตความคิดเห็นเรียบร้อยแล้ว'
        else:
            # Create new feedback
            feedback = Feedback(
                order_id=order.id,
                rating=int(rating),
                comment=comment
            )
            db.session.add(feedback)
            message = 'ขอบคุณสำหรับความคิดเห็นของคุณ'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500


@customer_bp.route('/api/order/status/<int:order_id>')
def get_order_status(order_id):
    """
    Get real-time order status
    Enhanced with more detailed information
    """
    try:
        order = Order.query.get_or_404(order_id)
        
        # Calculate estimated completion time
        estimated_completion = None
        if order.status in ['accepted', 'preparing']:
            # Estimate 15-30 minutes from acceptance
            if order.accepted_at:
                estimated_completion = order.accepted_at + timedelta(minutes=25)
            else:
                estimated_completion = get_thai_now() + timedelta(minutes=30)
        
        return jsonify({
            'success': True,
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'status_display': order.get_status_display(),
                'total_price': float(order.total_price),
                'created_at': order.created_at.isoformat(),
                'estimated_completion': estimated_completion.isoformat() if estimated_completion else None,
                'can_cancel': order.can_be_cancelled(),
                'can_modify': order.can_be_modified()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

# Cart management helper functions
def add_to_cart(menu_id, quantity, options=None, special_requests=None):
    """
    Add item to session cart
    
    Args:
        menu_id (int): Menu item ID
        quantity (int): Quantity to add
        options (list): Selected option IDs
        special_requests (str): Special requests text
    """
    
    menu = db.session.get(Menu, menu_id)
    if not menu or not menu.is_active:
        return False
    
    # Calculate item price including options
    base_price = float(menu.price)
    options_price = 0
    selected_options = []
    
    if options:
        option_items = MenuOptionItem.query.filter(
            MenuOptionItem.id.in_(options),
            MenuOptionItem.is_active == True
        ).all()
        
        for option in option_items:
            options_price += float(option.additional_price)
            selected_options.append({
                'id': option.id,
                'name': option.name,
                'price': float(option.additional_price)
            })
    
    total_price = (base_price + options_price) * quantity
    
    # Create cart item
    cart_item = {
        'id': str(uuid.uuid4()),  # Unique ID for cart management
        'menu_id': menu.id,
        'menu_name': menu.name,
        'base_price': base_price,
        'quantity': quantity,
        'options': selected_options,
        'special_requests': special_requests,
        'total_price': total_price
    }
    
    # Add to session cart
    if 'cart' not in session:
        session['cart'] = []
    
    session['cart'].append(cart_item)
    session.modified = True
    
    return True

def remove_from_cart(cart_item_id):
    """
    Remove item from session cart
    
    Args:
        cart_item_id (str): Cart item unique ID
    """
    
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != cart_item_id]
        session.modified = True

def update_cart_quantity(cart_item_id, new_quantity):
    """
    Update quantity of cart item
    
    Args:
        cart_item_id (str): Cart item unique ID
        new_quantity (int): New quantity
    """
    
    if 'cart' in session:
        for item in session['cart']:
            if item['id'] == cart_item_id:
                if new_quantity <= 0:
                    remove_from_cart(cart_item_id)
                else:
                    # Recalculate total price
                    options_price = sum(opt['price'] for opt in item['options'])
                    item['quantity'] = new_quantity
                    item['total_price'] = (item['base_price'] + options_price) * new_quantity
                    session.modified = True
                break

def clear_cart():
    """Clear all items from cart"""
    session.pop('cart', None)
    session.pop('selected_zone_id', None)
    session.modified = True

@customer_bp.route('/api/place-order', methods=['POST'])
def api_place_order():
    """
    Place order from cart with rate limiting and validation
    Enhanced for Phase 3
    """
    try:
        # Check rate limiting
        can_order, message = check_rate_limit()
        if not can_order:
            return jsonify({
                'success': False,
                'message': message
            }), 429  # Too Many Requests
        
        data = request.get_json()
        customer_name = data.get('customer_name', '').strip()
        customer_phone = data.get('customer_phone', '').strip()
        delivery_address = data.get('delivery_address', '').strip()
        special_instructions = data.get('special_instructions', '').strip()
        
        # Validation
        if not customer_name:
            return jsonify({
                'success': False,
                'message': 'กรุณาระบุชื่อลูกค้า'
            }), 400
        
        if not customer_phone:
            return jsonify({
                'success': False,
                'message': 'กรุณาระบุหมายเลขโทรศัพท์'
            }), 400
        
        # Get cart from session
        cart = session.get('cart', [])
        if not cart:
            return jsonify({
                'success': False,
                'message': 'ไม่มีรายการในตะกร้า'
            }), 400
        
        # Get delivery zone
        zone_id = session.get('selected_zone_id')
        zone = None
        if zone_id:
            zone = db.session.get(DeliveryZone, zone_id)
        
        # Calculate total price and validate menu items
        total_price = 0
        valid_items = []
        
        for cart_item in cart:
            menu = db.session.get(Menu, cart_item['menu_id'])
            if not menu or not menu.is_active:
                continue  # Skip inactive items
            
            # Validate options
            options_price = 0
            valid_options = []
            
            for option in cart_item.get('options', []):
                if option.get('id'):
                    option_item = db.session.get(MenuOptionItem, option['id'])
                    if option_item and option_item.is_active:
                        options_price += float(option_item.additional_price)
                        valid_options.append(option)
            
            # Recalculate item total
            item_total = (float(menu.price) + options_price) * cart_item['quantity']
            cart_item['options'] = valid_options
            cart_item['total_price'] = item_total
            
            valid_items.append(cart_item)
            total_price += item_total
        
        if not valid_items:
            return jsonify({
                'success': False,
                'message': 'ไม่มีรายการที่สามารถสั่งได้'
            }), 400
        
        # Create order
        order = Order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            total_price=total_price,
            zone_id=zone.id if zone else None,
            special_instructions=special_instructions
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items
        for cart_item in valid_items:
            menu = db.session.get(Menu, cart_item['menu_id'])
            
            order_item = OrderItem(
                order_id=order.id,
                menu_id=menu.id,
                menu_name=menu.name,
                quantity=cart_item['quantity'],
                price=cart_item['total_price'],
                special_requests=cart_item.get('special_requests')
            )
            db.session.add(order_item)
            db.session.flush()  # Get order item ID
            
            # Add options
            for option in cart_item.get('options', []):
                if option.get('id'):
                    option_item = db.session.get(MenuOptionItem, option['id'])
                    if option_item:
                        order_option = OrderItemOption(
                            order_item_id=order_item.id,
                            option_id=option_item.id,
                            option_name=option_item.name,
                            option_price=option_item.additional_price
                        )
                        db.session.add(order_option)
        
        # Record session activity for rate limiting
        customer_session = get_or_create_session()
        customer_session.record_order()
        
        db.session.commit()
        
        # Clear cart
        clear_cart()
        
        return jsonify({
            'success': True,
            'message': 'สั่งออเดอร์เรียบร้อยแล้ว',
            'order_id': order.id,
            'order_number': order.order_number,
            'total_price': float(order.total_price)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500
