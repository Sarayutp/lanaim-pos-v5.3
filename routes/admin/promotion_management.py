"""
Promotion Management Routes
Phase 2 - Marketing and Discount Management

Handles creation, editing, and management of promotions and discounts.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import json
from models import Promotion, Menu, Order, db, get_thai_now
from flask_login import current_user
from .auth import admin_required
from . import admin_bp


@admin_bp.route('/promotions')
@admin_required
def promotion_list():
    """List all promotions"""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')  # all, active, expired, inactive
    
    # Base query
    query = Promotion.query
    
    # Apply status filter
    now = get_thai_now()
    if status_filter == 'active':
        query = query.filter(
            Promotion.is_active == True,
            Promotion.start_date <= now,
            Promotion.end_date >= now
        )
    elif status_filter == 'expired':
        query = query.filter(Promotion.end_date < now)
    elif status_filter == 'inactive':
        query = query.filter(Promotion.is_active == False)
    
    promotions = query.order_by(Promotion.created_at.desc()).all()
    
    # Calculate statistics
    total_promotions = Promotion.query.count()
    active_promotions = Promotion.query.filter(
        Promotion.is_active == True,
        Promotion.start_date <= now,
        Promotion.end_date >= now
    ).count()
    
    return render_template('admin/promotions/list.html',
                         promotions=promotions,
                         total_promotions=total_promotions,
                         active_promotions=active_promotions,
                         status_filter=status_filter)


@admin_bp.route('/promotions/create', methods=['GET', 'POST'])
@admin_required
def promotion_create():
    """Create new promotion"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        promo_type = request.form.get('type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        minimum_order_amount = request.form.get('minimum_order_amount', '0')
        usage_limit = request.form.get('usage_limit', '')
        is_active = request.form.get('is_active') == 'on'
        
        # Type-specific fields
        discount_percentage = request.form.get('discount_percentage', '0')
        discount_amount = request.form.get('discount_amount', '0')
        buy_quantity = request.form.get('buy_quantity', '0')
        get_quantity = request.form.get('get_quantity', '0')
        applicable_menus = request.form.getlist('applicable_menus')
        
        # Validation
        if not name:
            flash('กรุณากรอกชื่อโปรโมชัน', 'error')
            return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        if not promo_type:
            flash('กรุณาเลือกประเภทโปรโมชัน', 'error')
            return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
            end_dt = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
            
            if end_dt <= start_dt:
                flash('วันที่สิ้นสุดต้องหลังจากวันที่เริ่มต้น', 'error')
                return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        except ValueError:
            flash('กรุณากรอกวันที่และเวลาที่ถูกต้อง', 'error')
            return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        try:
            minimum_order_amount = float(minimum_order_amount)
            if minimum_order_amount < 0:
                flash('จำนวนเงินขั้นต่ำต้องเป็นจำนวนบวก', 'error')
                return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        except ValueError:
            flash('กรุณากรอกจำนวนเงินขั้นต่ำที่ถูกต้อง', 'error')
            return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        # Usage limit validation
        usage_limit_int = None
        if usage_limit:
            try:
                usage_limit_int = int(usage_limit)
                if usage_limit_int <= 0:
                    flash('จำนวนครั้งที่ใช้ได้ต้องเป็นจำนวนบวก', 'error')
                    return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
            except ValueError:
                flash('กรุณากรอกจำนวนครั้งที่ใช้ได้ที่ถูกต้อง', 'error')
                return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        # Create promotion
        promotion = Promotion(
            name=name,
            description=description,
            type=promo_type,
            start_date=start_dt,
            end_date=end_dt,
            minimum_order_amount=minimum_order_amount,
            usage_limit=usage_limit_int,
            is_active=is_active,
            created_by=current_user.id
        )
        
        # Set type-specific fields
        if promo_type == 'percentage':
            try:
                promotion.discount_percentage = float(discount_percentage)
                if promotion.discount_percentage <= 0 or promotion.discount_percentage > 100:
                    flash('เปอร์เซ็นต์ส่วนลดต้องอยู่ระหว่าง 1-100', 'error')
                    return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
            except ValueError:
                flash('กรุณากรอกเปอร์เซ็นต์ส่วนลดที่ถูกต้อง', 'error')
                return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        elif promo_type == 'fixed_amount':
            try:
                promotion.discount_amount = float(discount_amount)
                if promotion.discount_amount <= 0:
                    flash('จำนวนเงินส่วนลดต้องเป็นจำนวนบวก', 'error')
                    return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
            except ValueError:
                flash('กรุณากรอกจำนวนเงินส่วนลดที่ถูกต้อง', 'error')
                return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        elif promo_type == 'buy_x_get_y':
            try:
                promotion.buy_quantity = int(buy_quantity)
                promotion.get_quantity = int(get_quantity)
                if promotion.buy_quantity <= 0 or promotion.get_quantity <= 0:
                    flash('จำนวนที่ซื้อและแถมต้องเป็นจำนวนบวก', 'error')
                    return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
            except ValueError:
                flash('กรุณากรอกจำนวนที่ซื้อและแถมที่ถูกต้อง', 'error')
                return render_template('admin/promotions/form.html', menus=Menu.query.filter_by(is_active=True).all())
        
        # Set applicable menus
        if applicable_menus:
            promotion.applicable_menu_ids = json.dumps([int(mid) for mid in applicable_menus])
        
        db.session.add(promotion)
        db.session.commit()
        
        flash(f'เพิ่มโปรโมชัน "{name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin.promotion_list'))
    
    # GET request - show form
    menus = Menu.query.filter_by(is_active=True).order_by(Menu.category, Menu.name).all()
    return render_template('admin/promotions/form.html', menus=menus)


@admin_bp.route('/promotions/<int:promotion_id>/edit', methods=['GET', 'POST'])
@admin_required
def promotion_edit(promotion_id):
    """Edit promotion"""
    promotion = Promotion.query.get_or_404(promotion_id)
    
    if request.method == 'POST':
        # Similar validation logic as create
        # (Implementation would be similar to promotion_create but updating existing promotion)
        pass
    
    # GET request - show edit form
    menus = Menu.query.filter_by(is_active=True).order_by(Menu.category, Menu.name).all()
    
    # Parse applicable menu IDs
    applicable_menu_ids = []
    if promotion.applicable_menu_ids:
        try:
            applicable_menu_ids = json.loads(promotion.applicable_menu_ids)
        except:
            pass
    
    return render_template('admin/promotions/form.html', 
                         promotion=promotion, 
                         menus=menus, 
                         applicable_menu_ids=applicable_menu_ids,
                         edit=True)


@admin_bp.route('/promotions/<int:promotion_id>')
@admin_required
def promotion_detail(promotion_id):
    """View promotion details and usage statistics"""
    promotion = Promotion.query.get_or_404(promotion_id)
    
    # Get applicable menus if any
    applicable_menus = []
    if promotion.applicable_menu_ids:
        try:
            menu_ids = json.loads(promotion.applicable_menu_ids)
            applicable_menus = Menu.query.filter(Menu.id.in_(menu_ids)).all()
        except:
            pass
    
    # Calculate usage statistics (simplified - would need to track actual usage)
    # For now, just show basic info
    stats = {
        'current_usage': promotion.current_usage,
        'usage_limit': promotion.usage_limit,
        'usage_percentage': (promotion.current_usage / promotion.usage_limit * 100) if promotion.usage_limit else 0,
        'days_remaining': (promotion.end_date - get_thai_now()).days if promotion.end_date > get_thai_now() else 0,
        'is_valid': promotion.is_valid_now()
    }
    
    return render_template('admin/promotions/detail.html', 
                         promotion=promotion, 
                         applicable_menus=applicable_menus,
                         stats=stats)


@admin_bp.route('/promotions/<int:promotion_id>/delete', methods=['POST'])
@admin_required
def promotion_delete(promotion_id):
    """Delete promotion"""
    promotion = Promotion.query.get_or_404(promotion_id)
    
    promotion_name = promotion.name
    db.session.delete(promotion)
    db.session.commit()
    
    flash(f'ลบโปรโมชัน "{promotion_name}" เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.promotion_list'))


@admin_bp.route('/api/promotions/<int:promotion_id>/toggle-status', methods=['POST'])
@admin_required
def api_promotion_toggle_status(promotion_id):
    """Toggle promotion active status"""
    promotion = Promotion.query.get_or_404(promotion_id)
    promotion.is_active = not promotion.is_active
    db.session.commit()
    
    status = 'เปิดใช้งาน' if promotion.is_active else 'ปิดใช้งาน'
    return jsonify({
        'success': True,
        'message': f'เปลี่ยนสถานะโปรโมชัน "{promotion.name}" เป็น {status}',
        'is_active': promotion.is_active
    })


@admin_bp.route('/api/promotions/active')
@admin_required
def api_active_promotions():
    """Get list of active promotions"""
    now = get_thai_now()
    promotions = Promotion.query.filter(
        Promotion.is_active == True,
        Promotion.start_date <= now,
        Promotion.end_date >= now
    ).all()
    
    promotion_list = []
    for promo in promotions:
        applicable_menus = []
        if promo.applicable_menu_ids:
            try:
                menu_ids = json.loads(promo.applicable_menu_ids)
                applicable_menus = menu_ids
            except:
                pass
        
        promotion_list.append({
            'id': promo.id,
            'name': promo.name,
            'description': promo.description,
            'type': promo.type,
            'discount_percentage': float(promo.discount_percentage) if promo.discount_percentage else None,
            'discount_amount': float(promo.discount_amount) if promo.discount_amount else None,
            'minimum_order_amount': float(promo.minimum_order_amount),
            'applicable_menu_ids': applicable_menus,
            'usage_remaining': (promo.usage_limit - promo.current_usage) if promo.usage_limit else None
        })
    
    return jsonify({'promotions': promotion_list})
