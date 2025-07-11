"""
Zone/Table Management Routes
Phase 2 - Delivery Zone and Table Management

Handles creation, editing, and management of delivery zones/tables
where customers can place orders.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from models import DeliveryZone, Order, db
from .auth import admin_required
from . import admin_bp


@admin_bp.route('/zones')
@admin_required
def zone_list():
    """List all delivery zones/tables"""
    zones = DeliveryZone.query.order_by(DeliveryZone.name).all()
    
    # Calculate statistics for each zone
    zone_stats = {}
    for zone in zones:
        # Count orders for each zone
        total_orders = Order.query.filter_by(delivery_zone_id=zone.id).count()
        active_orders = Order.query.filter_by(delivery_zone_id=zone.id)\
            .filter(Order.status.in_(['pending', 'accepted', 'preparing', 'ready', 'delivering'])).count()
        
        zone_stats[zone.id] = {
            'total_orders': total_orders,
            'active_orders': active_orders
        }
    
    return render_template('admin/zones/list.html', zones=zones, zone_stats=zone_stats)


@admin_bp.route('/zones/create', methods=['GET', 'POST'])
@admin_required
def zone_create():
    """Create new delivery zone/table"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        # Validation
        if not name:
            flash('กรุณากรอกชื่อโซน/โต๊ะ', 'error')
            return render_template('admin/zones/form.html')
        
        # Check for duplicate name
        existing = DeliveryZone.query.filter_by(name=name).first()
        if existing:
            flash('ชื่อโซน/โต๊ะนี้มีอยู่แล้ว', 'error')
            return render_template('admin/zones/form.html')
        
        # Create zone
        zone = DeliveryZone(
            name=name,
            description=description if description else None,
            is_active=is_active
        )
        
        db.session.add(zone)
        db.session.commit()
        
        flash(f'เพิ่มโซน/โต๊ะ "{name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin.zone_list'))
    
    return render_template('admin/zones/form.html')


@admin_bp.route('/zones/<int:zone_id>/edit', methods=['GET', 'POST'])
@admin_required
def zone_edit(zone_id):
    """Edit delivery zone/table"""
    zone = DeliveryZone.query.get_or_404(zone_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        # Validation
        if not name:
            flash('กรุณากรอกชื่อโซน/โต๊ะ', 'error')
            return render_template('admin/zones/form.html', zone=zone, edit=True)
        
        # Check for duplicate name (excluding current zone)
        existing = DeliveryZone.query.filter(
            DeliveryZone.name == name,
            DeliveryZone.id != zone_id
        ).first()
        if existing:
            flash('ชื่อโซน/โต๊ะนี้มีอยู่แล้ว', 'error')
            return render_template('admin/zones/form.html', zone=zone, edit=True)
        
        # Update zone
        zone.name = name
        zone.description = description if description else None
        zone.is_active = is_active
        
        db.session.commit()
        
        flash(f'แก้ไขโซน/โต๊ะ "{name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin.zone_list'))
    
    return render_template('admin/zones/form.html', zone=zone, edit=True)


@admin_bp.route('/zones/<int:zone_id>/delete', methods=['POST'])
@admin_required
def zone_delete(zone_id):
    """Delete delivery zone/table"""
    zone = DeliveryZone.query.get_or_404(zone_id)
    
    # Check if zone is used in any active orders
    active_orders = Order.query.filter_by(delivery_zone_id=zone_id)\
        .filter(Order.status.in_(['pending', 'accepted', 'preparing', 'ready', 'delivering'])).first()
    
    if active_orders:
        flash('ไม่สามารถลบโซน/โต๊ะที่มีออเดอร์ที่ยังไม่เสร็จสิ้น', 'error')
        return redirect(url_for('admin.zone_list'))
    
    zone_name = zone.name
    db.session.delete(zone)
    db.session.commit()
    
    flash(f'ลบโซน/โต๊ะ "{zone_name}" เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.zone_list'))


@admin_bp.route('/zones/<int:zone_id>')
@admin_required
def zone_detail(zone_id):
    """View zone details and order history"""
    zone = DeliveryZone.query.get_or_404(zone_id)
    
    # Get recent orders for this zone
    recent_orders = Order.query.filter_by(delivery_zone_id=zone_id)\
        .order_by(Order.created_at.desc()).limit(20).all()
    
    # Calculate statistics
    total_orders = Order.query.filter_by(delivery_zone_id=zone_id).count()
    completed_orders = Order.query.filter_by(delivery_zone_id=zone_id)\
        .filter(Order.status.in_(['delivered', 'completed'])).count()
    active_orders = Order.query.filter_by(delivery_zone_id=zone_id)\
        .filter(Order.status.in_(['pending', 'accepted', 'preparing', 'ready', 'delivering'])).count()
    
    # Calculate total revenue
    completed_order_list = Order.query.filter_by(delivery_zone_id=zone_id)\
        .filter(Order.status.in_(['delivered', 'completed'])).all()
    total_revenue = sum(float(order.total_price) for order in completed_order_list)
    
    stats = {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'active_orders': active_orders,
        'total_revenue': total_revenue,
        'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0
    }
    
    return render_template('admin/zones/detail.html', zone=zone, recent_orders=recent_orders, stats=stats)


@admin_bp.route('/api/zones/<int:zone_id>/toggle-status', methods=['POST'])
@admin_required
def api_zone_toggle_status(zone_id):
    """Toggle zone active status"""
    zone = DeliveryZone.query.get_or_404(zone_id)
    
    # Check if zone has active orders
    if zone.is_active:  # If trying to disable
        active_orders = Order.query.filter_by(delivery_zone_id=zone_id)\
            .filter(Order.status.in_(['pending', 'accepted', 'preparing', 'ready', 'delivering'])).first()
        
        if active_orders:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถปิดโซน/โต๊ะที่มีออเดอร์ที่ยังไม่เสร็จสิ้น'
            }), 400
    
    zone.is_active = not zone.is_active
    db.session.commit()
    
    status = 'เปิดใช้งาน' if zone.is_active else 'ปิดใช้งาน'
    return jsonify({
        'success': True,
        'message': f'เปลี่ยนสถานะโซน/โต๊ะ "{zone.name}" เป็น {status}',
        'is_active': zone.is_active
    })


@admin_bp.route('/api/zones/active')
@admin_required
def api_active_zones():
    """Get list of active zones for order placement"""
    zones = DeliveryZone.query.filter_by(is_active=True).order_by(DeliveryZone.name).all()
    
    zone_list = []
    for zone in zones:
        # Count current active orders
        active_orders = Order.query.filter_by(delivery_zone_id=zone.id)\
            .filter(Order.status.in_(['pending', 'accepted', 'preparing', 'ready', 'delivering'])).count()
        
        zone_list.append({
            'id': zone.id,
            'name': zone.name,
            'description': zone.description,
            'active_orders': active_orders
        })
    
    return jsonify({'zones': zone_list})
