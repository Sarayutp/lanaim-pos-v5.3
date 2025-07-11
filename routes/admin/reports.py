"""
Admin Reports Routes
Phase 2 - Business Intelligence and Analytics

Provides various reports for business analysis including sales reports,
inventory reports, and operational analytics.
"""

from flask import render_template, request, jsonify, make_response
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import json
from models import (
    Order, OrderItem, Menu, Ingredient, StockAdjustment,
    User, DeliveryZone, db, get_thai_now
)
from .auth import admin_required
from . import admin_bp


@admin_bp.route('/reports')
@admin_required
def reports_dashboard():
    """Reports dashboard with overview"""
    return render_template('admin/reports/dashboard.html')


@admin_bp.route('/reports/sales')
@admin_required
def sales_report():
    """Sales report with filtering options"""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    zone_id = request.args.get('zone_id')
    
    # Default to last 7 days if no dates provided
    if not start_date or not end_date:
        end_dt = get_thai_now().date()
        start_dt = end_dt - timedelta(days=6)
        start_date = start_dt.strftime('%Y-%m-%d')
        end_date = end_dt.strftime('%Y-%m-%d')
    else:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Build query
    query = Order.query.filter(
        func.date(Order.created_at) >= start_dt,
        func.date(Order.created_at) <= end_dt,
        Order.status.in_(['delivered', 'completed'])
    )
    
    if zone_id:
        query = query.filter_by(delivery_zone_id=int(zone_id))
    
    orders = query.all()
    
    # Calculate summary statistics
    total_orders = len(orders)
    total_revenue = sum(float(order.total_price) for order in orders)
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Daily breakdown
    daily_stats = {}
    current_date = start_dt
    while current_date <= end_dt:
        daily_orders = [o for o in orders if o.created_at.date() == current_date]
        daily_stats[current_date.strftime('%Y-%m-%d')] = {
            'date': current_date,
            'orders': len(daily_orders),
            'revenue': sum(float(o.total_price) for o in daily_orders)
        }
        current_date += timedelta(days=1)
    
    # Top selling items
    item_sales = {}
    for order in orders:
        for item in order.items:
            menu_name = item.menu.name
            if menu_name in item_sales:
                item_sales[menu_name]['quantity'] += item.quantity
                item_sales[menu_name]['revenue'] += float(item.total_price)
            else:
                item_sales[menu_name] = {
                    'menu': item.menu,
                    'quantity': item.quantity,
                    'revenue': float(item.total_price)
                }
    
    top_items = sorted(item_sales.values(), key=lambda x: x['quantity'], reverse=True)[:10]
    
    # Zone performance
    zone_stats = {}
    if not zone_id:  # Only show zone breakdown if not filtering by specific zone
        zones = DeliveryZone.query.filter_by(is_active=True).all()
        for zone in zones:
            zone_orders = [o for o in orders if o.delivery_zone_id == zone.id]
            zone_stats[zone.name] = {
                'zone': zone,
                'orders': len(zone_orders),
                'revenue': sum(float(o.total_price) for o in zone_orders)
            }
    
    # Get zones for filter dropdown
    zones = DeliveryZone.query.filter_by(is_active=True).order_by(DeliveryZone.name).all()
    
    return render_template('admin/reports/sales.html',
                         start_date=start_date,
                         end_date=end_date,
                         zone_id=int(zone_id) if zone_id else None,
                         zones=zones,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         average_order_value=average_order_value,
                         daily_stats=daily_stats,
                         top_items=top_items,
                         zone_stats=zone_stats)


@admin_bp.route('/reports/inventory')
@admin_required
def inventory_report():
    """Inventory and stock report"""
    # Get all ingredients with their current stock levels
    ingredients = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.name).all()
    
    # Calculate inventory value
    total_value = sum(
        float(ing.stock_quantity) * float(ing.cost_per_unit) 
        for ing in ingredients if ing.cost_per_unit
    )
    
    # Low stock items
    low_stock_items = [ing for ing in ingredients if ing.is_low_stock()]
    
    # Recent stock movements (last 30 days)
    thirty_days_ago = get_thai_now() - timedelta(days=30)
    recent_movements = StockAdjustment.query.filter(
        StockAdjustment.created_at >= thirty_days_ago
    ).order_by(desc(StockAdjustment.created_at)).limit(50).all()
    
    # Stock movement summary by type
    movement_summary = {
        'in': 0,
        'out': 0,
        'correction': 0
    }
    
    for movement in recent_movements:
        if movement.type in movement_summary:
            if movement.type == 'out':
                movement_summary[movement.type] += abs(float(movement.quantity))
            else:
                movement_summary[movement.type] += float(movement.quantity)
    
    # Top consumed ingredients (based on stock out movements)
    ingredient_consumption = {}
    out_movements = StockAdjustment.query.filter(
        StockAdjustment.type == 'out',
        StockAdjustment.created_at >= thirty_days_ago
    ).all()
    
    for movement in out_movements:
        ing_name = movement.ingredient.name
        if ing_name in ingredient_consumption:
            ingredient_consumption[ing_name]['quantity'] += abs(float(movement.quantity))
        else:
            ingredient_consumption[ing_name] = {
                'ingredient': movement.ingredient,
                'quantity': abs(float(movement.quantity))
            }
    
    top_consumed = sorted(ingredient_consumption.values(), key=lambda x: x['quantity'], reverse=True)[:10]
    
    return render_template('admin/reports/inventory.html',
                         ingredients=ingredients,
                         total_value=total_value,
                         low_stock_items=low_stock_items,
                         recent_movements=recent_movements,
                         movement_summary=movement_summary,
                         top_consumed=top_consumed)


@admin_bp.route('/reports/operations')
@admin_required
def operations_report():
    """Operational efficiency report"""
    # Get date range (last 7 days by default)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        end_dt = get_thai_now().date()
        start_dt = end_dt - timedelta(days=6)
    else:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get all orders in date range
    orders = Order.query.filter(
        func.date(Order.created_at) >= start_dt,
        func.date(Order.created_at) <= end_dt
    ).all()
    
    # Order status distribution
    status_counts = {}
    for status in ['pending', 'accepted', 'preparing', 'ready', 'delivering', 'delivered', 'completed', 'cancelled']:
        status_counts[status] = len([o for o in orders if o.status == status])
    
    # Average processing times (simplified calculation)
    completed_orders = [o for o in orders if o.status in ['delivered', 'completed']]
    
    # Calculate average fulfillment time
    fulfillment_times = []
    for order in completed_orders:
        if order.last_updated_at and order.created_at:
            time_diff = order.last_updated_at - order.created_at
            fulfillment_times.append(time_diff.total_seconds() / 60)  # Convert to minutes
    
    avg_fulfillment_time = sum(fulfillment_times) / len(fulfillment_times) if fulfillment_times else 0
    
    # Staff performance (orders handled)
    staff_performance = {}
    staff_users = User.query.filter(User.role.in_(['kitchen_staff', 'delivery_staff'])).all()
    
    for user in staff_users:
        # This is simplified - in a real system, you'd track which staff member handled each order
        staff_performance[user.username] = {
            'user': user,
            'orders_handled': 0,  # Would need to track this properly
            'last_active': user.last_login
        }
    
    # Peak hours analysis
    hourly_orders = {}
    for hour in range(24):
        hourly_orders[hour] = len([
            o for o in orders 
            if o.created_at.hour == hour
        ])
    
    peak_hours = sorted(hourly_orders.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return render_template('admin/reports/operations.html',
                         start_date=start_dt.strftime('%Y-%m-%d'),
                         end_date=end_dt.strftime('%Y-%m-%d'),
                         total_orders=len(orders),
                         status_counts=status_counts,
                         avg_fulfillment_time=avg_fulfillment_time,
                         staff_performance=staff_performance,
                         hourly_orders=hourly_orders,
                         peak_hours=peak_hours)


@admin_bp.route('/api/reports/sales-chart')
@admin_required
def api_sales_chart():
    """API endpoint for sales chart data"""
    days = int(request.args.get('days', 7))
    
    end_date = get_thai_now().date()
    start_date = end_date - timedelta(days=days-1)
    
    # Get sales data
    orders = Order.query.filter(
        func.date(Order.created_at) >= start_date,
        func.date(Order.created_at) <= end_date,
        Order.status.in_(['delivered', 'completed'])
    ).all()
    
    # Prepare chart data
    chart_data = []
    current_date = start_date
    
    while current_date <= end_date:
        daily_orders = [o for o in orders if o.created_at.date() == current_date]
        chart_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'orders': len(daily_orders),
            'revenue': sum(float(o.total_price) for o in daily_orders)
        })
        current_date += timedelta(days=1)
    
    return jsonify(chart_data)


@admin_bp.route('/api/reports/export/<report_type>')
@admin_required
def api_export_report(report_type):
    """Export report as CSV"""
    # This would implement CSV export functionality
    # For now, return a simple JSON response
    return jsonify({
        'message': f'Export functionality for {report_type} report would be implemented here',
        'type': report_type
    })
