"""
LanAim POS System v2.4 - Phase 1
Utility Functions and Helpers

This module contains utility functions and helpers used throughout the application.
"""

from functools import wraps
from flask import request, jsonify, session
from datetime import datetime, timedelta
import re

def validate_phone_number(phone):
    """
    Validate Thai phone number format
    
    Args:
        phone (str): Phone number to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Remove any non-digit characters
    phone_digits = re.sub(r'\D', '', phone)
    
    # Check if it's 9 or 10 digits and starts with appropriate numbers
    if len(phone_digits) == 10 and phone_digits.startswith(('08', '09', '06', '02')):
        return True
    elif len(phone_digits) == 9 and phone_digits.startswith(('8', '9', '6')):
        return True
    
    return False

def format_currency(amount):
    """
    Format amount as Thai currency
    
    Args:
        amount (float): Amount to format
    
    Returns:
        str: Formatted currency string
    """
    return f"฿{amount:,.2f}"

def get_order_status_display(status):
    """
    Get Thai display text for order status
    
    Args:
        status (str): Order status code
    
    Returns:
        str: Thai display text
    """
    status_map = {
        'pending': 'รอรับออเดอร์',
        'accepted': 'รับออเดอร์แล้ว',
        'preparing': 'กำลังเตรียม',
        'ready': 'พร้อมส่ง',
        'delivered': 'จัดส่งแล้ว',
        'completed': 'เสร็จสิ้น',
        'cancelled': 'ยกเลิก'
    }
    return status_map.get(status, status)

def get_payment_method_display(method):
    """
    Get Thai display text for payment method
    
    Args:
        method (str): Payment method code
    
    Returns:
        str: Thai display text
    """
    method_map = {
        'COD': 'ชำระเงินสดปลายทาง',
        'TOD': 'โอนจ่ายเมื่อรับของ'
    }
    return method_map.get(method, method)

def calculate_order_total(cart_items):
    """
    Calculate total price for cart items
    
    Args:
        cart_items (list): List of cart item dictionaries
    
    Returns:
        float: Total price
    """
    total = 0
    for item in cart_items:
        total += item.get('total_price', 0)
    return total

def rate_limit_check(identifier, max_requests=10, time_window=3600):
    """
    Basic rate limiting check (in-memory)
    
    Args:
        identifier (str): Unique identifier (IP, user ID, etc.)
        max_requests (int): Maximum requests allowed
        time_window (int): Time window in seconds
    
    Returns:
        bool: True if request is allowed, False if rate limited
    """
    # This is a simple in-memory rate limiter
    # In production, you'd want to use Redis or similar
    
    if not hasattr(rate_limit_check, 'requests'):
        rate_limit_check.requests = {}
    
    now = datetime.now()
    
    # Clean old entries
    rate_limit_check.requests = {
        key: value for key, value in rate_limit_check.requests.items()
        if value['reset_time'] > now
    }
    
    # Check current identifier
    if identifier not in rate_limit_check.requests:
        rate_limit_check.requests[identifier] = {
            'count': 1,
            'reset_time': now + timedelta(seconds=time_window)
        }
        return True
    
    entry = rate_limit_check.requests[identifier]
    if entry['count'] >= max_requests:
        return False
    
    entry['count'] += 1
    return True

def api_rate_limit(max_requests=10, time_window=3600):
    """
    Decorator for API rate limiting
    
    Args:
        max_requests (int): Maximum requests allowed
        time_window (int): Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use IP address as identifier
            identifier = request.remote_addr
            
            if not rate_limit_check(identifier, max_requests, time_window):
                return jsonify({
                    'error': 'ส่งคำขอบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่',
                    'code': 'RATE_LIMIT_EXCEEDED'
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_input(text, max_length=None):
    """
    Sanitize user input text
    
    Args:
        text (str): Input text to sanitize
        max_length (int): Maximum allowed length
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove dangerous characters and normalize whitespace
    sanitized = text.strip()
    sanitized = re.sub(r'[<>"\']', '', sanitized)
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Truncate if necessary
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

def validate_order_data(data):
    """
    Validate order data from API request
    
    Args:
        data (dict): Order data to validate
    
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    required_fields = ['customer_name', 'customer_phone', 'delivery_address', 'payment_method']
    
    for field in required_fields:
        if not data.get(field):
            return False, f'กรุณากรอก {field}'
    
    # Validate phone number
    if not validate_phone_number(data['customer_phone']):
        return False, 'เบอร์โทรศัพท์ไม่ถูกต้อง'
    
    # Validate payment method
    if data['payment_method'] not in ['COD', 'TOD']:
        return False, 'วิธีการชำระเงินไม่ถูกต้อง'
    
    # Sanitize text inputs
    data['customer_name'] = sanitize_input(data['customer_name'], 100)
    data['delivery_address'] = sanitize_input(data['delivery_address'], 500)
    
    return True, ""

def get_thai_datetime_string(dt):
    """
    Format datetime as Thai string
    
    Args:
        dt (datetime): Datetime object
    
    Returns:
        str: Formatted Thai datetime string
    """
    thai_months = [
        'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน',
        'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
        'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
    ]
    
    thai_year = dt.year + 543  # Convert to Buddhist Era
    thai_month = thai_months[dt.month - 1]
    
    return f"{dt.day} {thai_month} {thai_year} เวลา {dt.strftime('%H:%M น.')}"

def generate_order_summary_text(order):
    """
    Generate text summary for order (useful for printing, SMS, etc.)
    
    Args:
        order (Order): Order object
    
    Returns:
        str: Text summary of order
    """
    lines = [
        "=" * 40,
        "ลานอิ่ม - ใบสั่งอาหาร",
        "=" * 40,
        f"ออเดอร์: {order.order_number}",
        f"เวลา: {order.created_at.strftime('%d/%m/%Y %H:%M น.')}",
        f"ลูกค้า: {order.customer_name}",
        f"เบอร์: {order.customer_phone}",
        f"ที่อยู่: {order.delivery_address_details}",
        "",
        "รายการอาหาร:",
        "-" * 40
    ]
    
    total = 0
    for item in order.items:
        item_total = item.get_total_price()
        total += item_total
        
        lines.append(f"{item.menu_name} x{item.quantity}")
        lines.append(f"  ราคา: {format_currency(item_total)}")
        
        # Add options
        for option in item.options:
            if option.option_price > 0:
                lines.append(f"  + {option.option_name} (+{format_currency(option.option_price)})")
            else:
                lines.append(f"  + {option.option_name}")
        
        # Add special requests
        if item.special_requests:
            lines.append(f"  หมายเหตุ: {item.special_requests}")
        
        lines.append("")
    
    lines.extend([
        "-" * 40,
        f"ยอดรวม: {format_currency(total)}",
        f"การชำระ: {get_payment_method_display(order.payment_method)}",
        "=" * 40
    ])
    
    return "\n".join(lines)

class CartManager:
    """Helper class for managing session cart"""
    
    @staticmethod
    def get_cart():
        """Get cart from session"""
        return session.get('cart', [])
    
    @staticmethod
    def add_item(menu_id, quantity, options=None, special_requests=None):
        """Add item to cart"""
        from routes.customer import add_to_cart
        return add_to_cart(menu_id, quantity, options, special_requests)
    
    @staticmethod
    def remove_item(cart_item_id):
        """Remove item from cart"""
        from routes.customer import remove_from_cart
        remove_from_cart(cart_item_id)
    
    @staticmethod
    def update_quantity(cart_item_id, new_quantity):
        """Update item quantity"""
        from routes.customer import update_cart_quantity
        update_cart_quantity(cart_item_id, new_quantity)
    
    @staticmethod
    def clear():
        """Clear cart"""
        from routes.customer import clear_cart
        clear_cart()
    
    @staticmethod
    def get_total():
        """Get cart total"""
        cart = CartManager.get_cart()
        return sum(item.get('total_price', 0) for item in cart)
    
    @staticmethod
    def get_count():
        """Get cart item count"""
        return len(CartManager.get_cart())

# Template filters and functions
def register_template_filters(app):
    """Register custom template filters"""
    
    @app.template_filter('currency')
    def currency_filter(amount):
        return format_currency(float(amount))
    
    @app.template_filter('thai_datetime')
    def thai_datetime_filter(dt):
        return get_thai_datetime_string(dt)
    
    @app.template_filter('order_status')
    def order_status_filter(status):
        return get_order_status_display(status)
    
    @app.template_filter('payment_method')
    def payment_method_filter(method):
        return get_payment_method_display(method)
    
    @app.template_global('get_progress_width')
    def get_progress_width(status):
        """Get progress bar width for order status"""
        progress_map = {
            'pending': 0,          # รอรับออเดอร์
            'accepted': 17.2,      # รับออเดอร์แล้ว (86 / 5 = 17.2%)
            'preparing': 34.4,     # กำลังเตรียม (17.2 * 2)
            'ready': 51.6,         # พร้อมส่ง (17.2 * 3)
            'delivering': 68.8,    # กำลังจัดส่ง (17.2 * 4)
            'delivered': 86.0,     # จัดส่งแล้ว (17.2 * 5) - เท่ากับ background line
            'completed': 86.0,     # เสร็จสิ้น (เหมือน delivered)
            'cancelled': 0
        }
        return progress_map.get(status, 0)
