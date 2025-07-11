"""
Admin Dashboard Routes
Phase 2 - Main Admin Dashboard and Overview

Provides overview of restaurant operations, recent activities,
and quick access to management functions.
"""

from flask import render_template, jsonify
from flask_login import current_user
from sqlalchemy import func
from datetime import datetime, timedelta
from models import (
    Order, Menu, Ingredient, User, StockAdjustment, 
    Promotion, DeliveryZone, get_thai_now
)
from .auth import admin_required
from . import admin_bp


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Main admin dashboard"""
    # Get today's date range
    today = get_thai_now().date()
    tomorrow = today + timedelta(days=1)
    
    # Order statistics for today
    today_orders = Order.query.filter(
        func.date(Order.created_at) == today
    ).all()
    
    # Calculate statistics
    stats = {
        'total_orders_today': len(today_orders),
        'total_revenue_today': sum(float(order.total_price) for order in today_orders),
        'pending_orders': len([o for o in today_orders if o.status == 'pending']),
        'completed_orders': len([o for o in today_orders if o.status in ['delivered', 'completed']]),
        'total_menus': Menu.query.filter_by(is_active=True).count(),
        'total_ingredients': Ingredient.query.count(),
        'low_stock_items': Ingredient.query.filter(
            Ingredient.stock_quantity <= Ingredient.low_stock_threshold
        ).count(),
        'active_promotions': 0  # Will implement later
    }
    
    # Recent orders (last 10)
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Low stock alerts
    low_stock_items = Ingredient.query.filter(
        Ingredient.stock_quantity <= Ingredient.low_stock_threshold
    ).all()
    
    # Recent stock adjustments
    recent_stock_adjustments = []  # Will implement later
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_orders=recent_orders,
                         low_stock_items=low_stock_items,
                         recent_stock_adjustments=recent_stock_adjustments)


@admin_bp.route('/api/dashboard/stats')
@admin_required
def api_dashboard_stats():
    """API endpoint for dashboard statistics (for AJAX updates)"""
    # Get today's date range
    today = get_thai_now().date()
    
    # Order statistics for today
    today_orders = Order.query.filter(
        func.date(Order.created_at) == today
    ).all()
    
    # Order status distribution
    status_counts = {}
    for status in ['pending', 'accepted', 'preparing', 'ready', 'delivering', 'delivered', 'completed', 'cancelled']:
        status_counts[status] = len([o for o in today_orders if o.status == status])
    
    # Hourly sales data (last 24 hours)
    now = get_thai_now()
    hourly_sales = []
    for i in range(24):
        hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
        hour_end = hour_start + timedelta(hours=1)
        
        hour_orders = Order.query.filter(
            Order.created_at >= hour_start,
            Order.created_at < hour_end,
            Order.status.in_(['delivered', 'completed'])
        ).all()
        
        hourly_sales.append({
            'hour': hour_start.strftime('%H:00'),
            'revenue': sum(float(order.total_price) for order in hour_orders),
            'orders': len(hour_orders)
        })
    
    hourly_sales.reverse()  # Show oldest to newest
    
    return jsonify({
        'status_counts': status_counts,
        'hourly_sales': hourly_sales,
        'total_revenue_today': sum(float(order.total_price) for order in today_orders),
        'total_orders_today': len(today_orders)
    })


@admin_bp.route('/api/dashboard/recent-activity')
@admin_required
def api_recent_activity():
    """API endpoint for recent activity feed"""
    activities = []
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    for order in recent_orders:
        activities.append({
            'type': 'order',
            'message': f'ออเดอร์ใหม่: {order.order_number} (฿{order.total_price})',
            'time': order.created_at.strftime('%H:%M'),
            'status': order.status
        })
    
    # Recent stock adjustments
    recent_adjustments = StockAdjustment.query.order_by(
        StockAdjustment.created_at.desc()
    ).limit(5).all()
    
    for adj in recent_adjustments:
        if adj.type == 'in':
            message = f'เพิ่มสต็อก: {adj.ingredient.name} (+{adj.quantity} {adj.ingredient.unit})'
        elif adj.type == 'out':
            message = f'ใช้สต็อก: {adj.ingredient.name} (-{abs(adj.quantity)} {adj.ingredient.unit})'
        else:
            message = f'ปรับสต็อก: {adj.ingredient.name} ({adj.quantity:+} {adj.ingredient.unit})'
        
        activities.append({
            'type': 'stock',
            'message': message,
            'time': adj.created_at.strftime('%H:%M'),
            'user': adj.adjusted_by_user.username if adj.adjusted_by_user else 'System'
        })
    
    # Sort by time (most recent first)
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return jsonify({'activities': activities[:10]})  # Return top 10
