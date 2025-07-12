"""
LanAim POS System v2.4 - Phase 1
Staff Routes Blueprint

This module handles all staff-facing routes including:
- Staff authentication
- Order management dashboard
- Order status updates
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Order, OrderItem
from datetime import datetime
from functools import wraps

def staff_required(f):
    """
    Decorator to require staff authentication and appropriate permissions
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('staff.login'))
        
        # Check if user is staff (role is staff, kitchen_staff, delivery_staff, or admin)
        if current_user.role not in ['staff', 'kitchen_staff', 'delivery_staff', 'admin']:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('staff.login'))
        
        return f(*args, **kwargs)
    return decorated_function

# Create staff blueprint
staff_bp = Blueprint('staff', __name__)

@staff_bp.route('/')
def index():
    """
    Staff index page - redirect to dashboard if logged in, otherwise to login
    """
    if current_user.is_authenticated:
        return redirect(url_for('staff.dashboard'))
    else:
        return redirect(url_for('staff.login'))

@staff_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Staff login page and authentication
    """
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน', 'error')
            return render_template('staff/login.html')
        
        # Find user by username
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.check_password(password):
            # Successful login
            login_user(user, remember=True)
            user.update_last_login()
            
            flash(f'เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ {username}', 'success')
            
            # Redirect based on role
            if user.role == 'kitchen_staff':
                return redirect(url_for('staff.kitchen_dashboard'))
            elif user.role == 'delivery_staff':
                return redirect(url_for('staff.delivery_dashboard'))
            else:
                return redirect(url_for('staff.dashboard'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    
    return render_template('staff/login.html')

@staff_bp.route('/logout')
@login_required
def logout():
    """Staff logout"""
    logout_user()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('staff.login'))

@staff_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Main staff dashboard - redirects based on role
    """
    
    if current_user.role == 'kitchen_staff':
        return redirect(url_for('staff.kitchen_dashboard'))
    elif current_user.role == 'delivery_staff':
        return redirect(url_for('staff.delivery_dashboard'))
    else:
        # Default dashboard for other roles
        return render_template('staff/dashboard.html')

@staff_bp.route('/kitchen')
@login_required
def kitchen_dashboard():
    """
    Kitchen staff dashboard
    Shows orders that need kitchen attention
    """
    
    # Only kitchen staff can access
    if current_user.role != 'kitchen_staff':
        flash('ไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('staff.dashboard'))
    
    # Get orders by status
    pending_orders = Order.query.filter_by(status='pending').order_by(Order.created_at.asc()).all()
    preparing_orders = Order.query.filter_by(status='preparing').order_by(Order.created_at.asc()).all()
    ready_orders = Order.query.filter_by(status='ready').order_by(Order.created_at.asc()).all()
    
    return render_template('staff/kitchen_dashboard.html',
                         pending_orders=pending_orders,
                         preparing_orders=preparing_orders,
                         ready_orders=ready_orders)

@staff_bp.route('/delivery')
@login_required
def delivery_dashboard():
    """
    Delivery staff dashboard
    Shows orders that need delivery attention
    """
    
    # Only delivery staff and admin can access
    if current_user.role not in ['delivery_staff', 'admin']:
        flash('ไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('staff.dashboard'))
    
    # Get orders by status
    ready_orders = Order.query.filter_by(status='ready').order_by(Order.created_at.asc()).all()
    delivering_orders = Order.query.filter_by(status='delivering').order_by(Order.created_at.asc()).all()
    
    # Calculate statistics
    today = datetime.now().date()
    
    # Count delivered orders today
    delivered_today_count = 0
    total_today_amount = 0.0
    
    for order in Order.query.filter_by(status='delivered').all():
        if order.last_updated_at and order.last_updated_at.date() == today:
            delivered_today_count += 1
            total_today_amount += float(order.total_price or 0)
    
    stats = {
        'ready_for_delivery': len(ready_orders),
        'delivering': len(delivering_orders),
        'delivered_today': delivered_today_count,
        'total_today': total_today_amount
    }
    
    return render_template('staff/delivery_dashboard.html',
                         ready_orders=ready_orders,
                         delivering_orders=delivering_orders,
                         stats=stats,
                         now=datetime.now())

@staff_bp.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    """
    Order details page for staff
    
    Args:
        order_id (int): Order ID to view
    """
    
    order = Order.query.get_or_404(order_id)
    
    return render_template('staff/order_details.html', order=order)

@staff_bp.route('/orders')
@login_required
def orders_list():
    """
    List all orders with filtering options
    """
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    date_filter = request.args.get('date', 'today')
    
    # Base query
    query = Order.query
    
    # Apply status filter
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Apply date filter
    if date_filter == 'today':
        from datetime import date
        today = date.today()
        query = query.filter(db.func.date(Order.created_at) == today)
    
    # Order by creation time (newest first)
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('staff/orders_list.html',
                         orders=orders,
                         current_status=status_filter,
                         current_date=date_filter)

# Order management functions
def can_update_order_status(order, user, new_status):
    """
    Check if user can update order to new status
    
    Args:
        order (Order): Order object
        user (User): Current user
        new_status (str): Desired new status
    
    Returns:
        bool: True if update is allowed
    """
    
    # Status transition rules based on user role
    if user.role == 'kitchen_staff':
        allowed_transitions = {
            'pending': ['preparing', 'cancelled'],  # Kitchen can accept orders directly to preparing
            'preparing': ['ready', 'cancelled'],    # Kitchen can complete cooking
            'ready': ['ready']                      # Kitchen can keep as ready
        }
    elif user.role == 'delivery_staff':
        allowed_transitions = {
            'ready': ['delivering'],               # Delivery can start delivery
            'delivering': ['delivered'],          # Delivery can complete delivery
            'delivered': ['delivered']            # Keep as delivered
        }
    else:
        # Other roles have no update permissions
        return False
    
    current_status = order.status
    return new_status in allowed_transitions.get(current_status, [])
