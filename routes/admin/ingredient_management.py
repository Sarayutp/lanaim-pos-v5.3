"""
Ingredient and Stock Management Routes
Phase 2 - Inventory Management

Handles ingredient management, stock adjustments, BOM (Bill of Materials),
and stock level monitoring.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import desc, func
from flask_login import current_user
from models import (
    Ingredient, RecipeBOM, StockAdjustment, Menu, 
    db, get_thai_now
)
from .auth import admin_required
from . import admin_bp


@admin_bp.route('/ingredients')
@admin_required
def ingredient_list():
    """List all ingredients with stock levels"""
    # Get filter parameters
    search = request.args.get('search', '').strip()
    low_stock_only = request.args.get('low_stock') == '1'
    
    # Base query
    query = Ingredient.query.filter_by(is_active=True)
    
    # Apply filters
    if search:
        query = query.filter(Ingredient.name.contains(search))
    
    if low_stock_only:
        query = query.filter(Ingredient.stock_quantity <= Ingredient.low_stock_threshold)
    
    ingredients = query.order_by(Ingredient.name).all()
    
    # Calculate statistics
    total_ingredients = Ingredient.query.filter_by(is_active=True).count()
    low_stock_count = Ingredient.query.filter(
        Ingredient.stock_quantity <= Ingredient.low_stock_threshold,
        Ingredient.is_active == True
    ).count()
    
    return render_template('admin/ingredients/list.html',
                         ingredients=ingredients,
                         total_ingredients=total_ingredients,
                         low_stock_count=low_stock_count,
                         search=search,
                         low_stock_only=low_stock_only)


@admin_bp.route('/ingredients/create', methods=['GET', 'POST'])
@admin_required
def ingredient_create():
    """Create new ingredient"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        unit = request.form.get('unit', '').strip()
        stock_quantity = request.form.get('stock_quantity', '0')
        low_stock_threshold = request.form.get('low_stock_threshold', '0')
        cost_per_unit = request.form.get('cost_per_unit', '0')
        is_active = request.form.get('is_active') == 'on'
        
        # Validation
        if not name:
            flash('กรุณากรอกชื่อวัตถุดิบ', 'error')
            return render_template('admin/ingredients/form.html')
        
        if not unit:
            flash('กรุณาเลือกหน่วยนับ', 'error')
            return render_template('admin/ingredients/form.html')
        
        try:
            stock_quantity = float(stock_quantity)
            low_stock_threshold = float(low_stock_threshold)
            cost_per_unit = float(cost_per_unit) if cost_per_unit else None
            
            if stock_quantity < 0 or low_stock_threshold < 0:
                raise ValueError("จำนวนต้องเป็นจำนวนบวก")
            
        except ValueError as e:
            flash(f'ข้อมูลไม่ถูกต้อง: {str(e)}', 'error')
            return render_template('admin/ingredients/form.html')
        
        # Check for duplicate name
        existing = Ingredient.query.filter_by(name=name).first()
        if existing:
            flash('ชื่อวัตถุดิบนี้มีอยู่แล้ว', 'error')
            return render_template('admin/ingredients/form.html')
        
        # Create ingredient
        ingredient = Ingredient(
            name=name,
            description=description,
            category=category if category else None,
            unit=unit,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            cost_per_unit=cost_per_unit,
            is_active=is_active
        )
        
        db.session.add(ingredient)
        db.session.commit()
        
        flash(f'เพิ่มวัตถุดิบ "{name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin.ingredient_list'))
    
    return render_template('admin/ingredients/form.html')


@admin_bp.route('/ingredients/<int:ingredient_id>/edit', methods=['GET', 'POST'])
@admin_required
def ingredient_edit(ingredient_id):
    """Edit ingredient"""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        unit = request.form.get('unit', '').strip()
        stock_quantity = request.form.get('stock_quantity', '0')
        low_stock_threshold = request.form.get('low_stock_threshold', '0')
        cost_per_unit = request.form.get('cost_per_unit', '0')
        is_active = request.form.get('is_active') == 'on'
        
        # Validation
        if not name:
            flash('กรุณากรอกชื่อวัตถุดิบ', 'error')
            return render_template('admin/ingredients/form.html', ingredient=ingredient, edit=True)
        
        if not unit:
            flash('กรุณาเลือกหน่วยนับ', 'error')
            return render_template('admin/ingredients/form.html', ingredient=ingredient, edit=True)
        
        try:
            stock_quantity = float(stock_quantity)
            low_stock_threshold = float(low_stock_threshold)
            cost_per_unit = float(cost_per_unit) if cost_per_unit else None
            
            if stock_quantity < 0 or low_stock_threshold < 0:
                raise ValueError("จำนวนต้องเป็นจำนวนบวก")
            
        except ValueError as e:
            flash(f'ข้อมูลไม่ถูกต้อง: {str(e)}', 'error')
            return render_template('admin/ingredients/form.html', ingredient=ingredient, edit=True)
        
        # Check for duplicate name (excluding current ingredient)
        existing = Ingredient.query.filter(
            Ingredient.name == name, 
            Ingredient.id != ingredient_id
        ).first()
        if existing:
            flash('ชื่อวัตถุดิบนี้มีอยู่แล้ว', 'error')
            return render_template('admin/ingredients/form.html', ingredient=ingredient, edit=True)
        
        # Update ingredient
        ingredient.name = name
        ingredient.description = description
        ingredient.category = category if category else None
        ingredient.unit = unit
        ingredient.stock_quantity = stock_quantity
        ingredient.low_stock_threshold = low_stock_threshold
        ingredient.cost_per_unit = cost_per_unit
        ingredient.is_active = is_active
        
        db.session.commit()
        
        flash(f'แก้ไขวัตถุดิบ "{name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin.ingredient_list'))
    
    return render_template('admin/ingredients/form.html', ingredient=ingredient, edit=True)


@admin_bp.route('/ingredients/<int:ingredient_id>/delete', methods=['POST'])
@admin_required
def ingredient_delete(ingredient_id):
    """Delete ingredient"""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    
    # Check if ingredient is used in any recipes
    recipes = RecipeBOM.query.filter_by(ingredient_id=ingredient_id, is_active=True).first()
    if recipes:
        flash('ไม่สามารถลบวัตถุดิบที่ใช้ในสูตรอาหาร', 'error')
        return redirect(url_for('admin.ingredient_list'))
    
    ingredient_name = ingredient.name
    ingredient.is_active = False  # Soft delete
    db.session.commit()
    
    flash(f'ลบวัตถุดิบ "{ingredient_name}" เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.ingredient_list'))


@admin_bp.route('/api/ingredient/<int:ingredient_id>/adjust-stock', methods=['POST'])
@admin_required
def api_ingredient_adjust_stock(ingredient_id):
    """Adjust ingredient stock"""
    try:
        ingredient = Ingredient.query.get_or_404(ingredient_id)
        data = request.get_json()
        
        adjustment_type = data.get('type')  # 'in' or 'out'
        quantity = float(data.get('quantity', 0))
        reason = data.get('reason', '')
        notes = data.get('notes', '')
        
        if quantity <= 0:
            return jsonify({'error': 'จำนวนต้องมากกว่า 0'}), 400
        
        # Calculate new stock
        if adjustment_type == 'in':
            new_stock = ingredient.stock_quantity + quantity
        elif adjustment_type == 'out':
            new_stock = ingredient.stock_quantity - quantity
            if new_stock < 0:
                return jsonify({'error': 'สต็อกไม่เพียงพอ'}), 400
        else:
            return jsonify({'error': 'ประเภทการปรับสต็อกไม่ถูกต้อง'}), 400
        
        # Create stock adjustment record
        adjustment = StockAdjustment(
            ingredient_id=ingredient_id,
            adjustment_type=adjustment_type,
            quantity_before=ingredient.stock_quantity,
            quantity_after=new_stock,
            adjustment_quantity=quantity,
            reason=reason,
            notes=notes,
            adjusted_by=current_user.id if current_user.is_authenticated else None
        )
        
        # Update ingredient stock
        ingredient.stock_quantity = new_stock
        
        db.session.add(adjustment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'ปรับสต็อก "{ingredient.name}" เรียบร้อยแล้ว',
            'new_stock': new_stock,
            'unit': ingredient.unit
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500


@admin_bp.route('/bom')
@admin_required
def bom_list():
    """List all Bill of Materials (recipes)"""
    # Get all menu items with their recipes
    menus_with_recipes = db.session.query(Menu)\
        .join(RecipeBOM, Menu.id == RecipeBOM.menu_id)\
        .filter(RecipeBOM.is_active == True)\
        .distinct().all()
    
    # Get menus without recipes
    menus_without_recipes = Menu.query\
        .filter(~Menu.id.in_(
            db.session.query(RecipeBOM.menu_id)
            .filter(RecipeBOM.is_active == True)
            .distinct()
        ))\
        .filter(Menu.is_active == True)\
        .all()
    
    return render_template('admin/bom/list.html',
                         menus_with_recipes=menus_with_recipes,
                         menus_without_recipes=menus_without_recipes)


@admin_bp.route('/bom/<int:menu_id>')
@admin_required
def bom_detail(menu_id):
    """View/Edit BOM for specific menu"""
    menu = Menu.query.get_or_404(menu_id)
    recipe_items = RecipeBOM.query.filter_by(menu_id=menu_id, is_active=True).all()
    available_ingredients = Ingredient.query.filter_by(is_active=True)\
        .order_by(Ingredient.name).all()
    
    return render_template('admin/bom/detail.html',
                         menu=menu,
                         recipe_items=recipe_items,
                         available_ingredients=available_ingredients)


@admin_bp.route('/bom/<int:menu_id>/add-ingredient', methods=['POST'])
@admin_required
def bom_add_ingredient(menu_id):
    """Add ingredient to BOM"""
    menu = Menu.query.get_or_404(menu_id)
    
    ingredient_id = request.form.get('ingredient_id')
    quantity = request.form.get('quantity', '0')
    notes = request.form.get('notes', '').strip()
    
    try:
        ingredient_id = int(ingredient_id)
        quantity = float(quantity)
        
        if quantity <= 0:
            flash('จำนวนต้องมากกว่า 0', 'error')
            return redirect(url_for('admin.bom_detail', menu_id=menu_id))
    except ValueError:
        flash('กรุณากรอกข้อมูลที่ถูกต้อง', 'error')
        return redirect(url_for('admin.bom_detail', menu_id=menu_id))
    
    # Check if ingredient exists
    ingredient = db.session.get(Ingredient, ingredient_id)
    if not ingredient:
        flash('ไม่พบวัตถุดิบที่เลือก', 'error')
        return redirect(url_for('admin.bom_detail', menu_id=menu_id))
    
    # Check if already exists
    existing = RecipeBOM.query.filter_by(
        menu_id=menu_id,
        ingredient_id=ingredient_id,
        is_active=True
    ).first()
    
    if existing:
        flash('วัตถุดิบนี้มีในสูตรแล้ว', 'error')
        return redirect(url_for('admin.bom_detail', menu_id=menu_id))
    
    # Add to BOM
    bom_item = RecipeBOM(
        menu_id=menu_id,
        ingredient_id=ingredient_id,
        quantity_used=quantity,
        notes=notes if notes else None
    )
    
    db.session.add(bom_item)
    db.session.commit()
    
    flash(f'เพิ่ม {ingredient.name} ลงในสูตร {menu.name} เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.bom_detail', menu_id=menu_id))


@admin_bp.route('/api/ingredients/low-stock')
@admin_required
def api_low_stock_ingredients():
    """API endpoint for low stock alerts"""
    low_stock_items = Ingredient.query.filter(
        Ingredient.stock_quantity <= Ingredient.low_stock_threshold,
        Ingredient.is_active == True
    ).all()
    
    items = []
    for item in low_stock_items:
        items.append({
            'id': item.id,
            'name': item.name,
            'current_stock': float(item.stock_quantity),
            'threshold': float(item.low_stock_threshold),
            'unit': item.unit,
            'supplier': item.supplier
        })
    
    return jsonify({'items': items})
