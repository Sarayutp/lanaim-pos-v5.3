"""
Menu Management Routes
Phase 2 - Menu CRUD Operations

Handles menu item creation, editing, deletion, and option management.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from PIL import Image
from models import Menu, MenuOptionGroup, MenuOptionItem, db
from .auth import admin_required
from . import admin_bp

# Image configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_menu_image(file):
    """Save uploaded menu image with optimization"""
    if not file or not file.filename:
        return None
    
    if not allowed_file(file.filename):
        raise ValueError('ไฟล์รูปภาพไม่ถูกต้อง')
    
    if file.content_length and file.content_length > MAX_IMAGE_SIZE:
        raise ValueError('ไฟล์รูปภาพใหญ่เกินไป (สูงสุด 5MB)')
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_{name}{ext}"
    
    # Create upload directory
    upload_dir = os.path.join(current_app.static_folder, 'images', 'menu')
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_filename)
    
    try:
        # Save and optimize image
        file.save(file_path)
        
        # Optimize image using PIL
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large (max 800x600)
            max_size = (800, 600)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            img.save(file_path, 'JPEG', quality=85, optimize=True)
        
        return f'/static/images/menu/{unique_filename}'
        
    except Exception as e:
        # Clean up file if something went wrong
        if os.path.exists(file_path):
            os.remove(file_path)
        raise ValueError(f'ไม่สามารถบันทึกรูปภาพได้: {str(e)}')

def delete_menu_image(image_url):
    """Delete menu image file"""
    if not image_url:
        return
    
    try:
        # Extract filename from URL
        filename = image_url.split('/')[-1]
        file_path = os.path.join(current_app.static_folder, 'images', 'menu', filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass  # Silent fail for image deletion


@admin_bp.route('/menu')
@admin_required
def menu_list():
    """List all menu items"""
    menus = Menu.query.order_by(Menu.category, Menu.name).all()
    categories = db.session.query(Menu.category).distinct().filter(Menu.category.isnot(None)).all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('admin/menu/list.html', menus=menus, categories=categories)


@admin_bp.route('/menu/create', methods=['GET', 'POST'])
@admin_required
def menu_create():
    """Create new menu item"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')
        category = request.form.get('category', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        # Validation
        if not name:
            flash('กรุณากรอกชื่อเมนู', 'error')
            return render_template('admin/menu/form.html')
        
        try:
            price = float(price)
            if price < 0:
                flash('ราคาต้องเป็นจำนวนบวก', 'error')
                return render_template('admin/menu/form.html')
        except ValueError:
            flash('กรุณากรอกราคาที่ถูกต้อง', 'error')
            return render_template('admin/menu/form.html')
        
        # Check for duplicate name
        existing = Menu.query.filter_by(name=name).first()
        if existing:
            flash('ชื่อเมนูนี้มีอยู่แล้ว', 'error')
            return render_template('admin/menu/form.html')
        
        # Create menu item
        menu = Menu(
            name=name,
            description=description,
            price=price,
            category=category if category else None,
            is_active=is_active
        )
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                try:
                    menu.image_url = save_menu_image(file)
                except ValueError as e:
                    flash(str(e), 'error')
                    return render_template('admin/menu/form.html')
        
        db.session.add(menu)
        db.session.commit()
        
        flash(f'เพิ่มเมนู "{name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin.menu_list'))
    
    return render_template('admin/menu/form.html')


@admin_bp.route('/menu/<int:menu_id>/edit', methods=['GET', 'POST'])
@admin_required
def menu_edit(menu_id):
    """Edit menu item"""
    menu = Menu.query.get_or_404(menu_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')
        category = request.form.get('category', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        # Validation
        if not name:
            flash('กรุณากรอกชื่อเมนู', 'error')
            return render_template('admin/menu/form.html', menu=menu, edit=True)
        
        try:
            price = float(price)
            if price < 0:
                flash('ราคาต้องเป็นจำนวนบวก', 'error')
                return render_template('admin/menu/form.html', menu=menu, edit=True)
        except ValueError:
            flash('กรุณากรอกราคาที่ถูกต้อง', 'error')
            return render_template('admin/menu/form.html', menu=menu, edit=True)
        
        # Check for duplicate name (excluding current menu)
        existing = Menu.query.filter(Menu.name == name, Menu.id != menu_id).first()
        if existing:
            flash('ชื่อเมนูนี้มีอยู่แล้ว', 'error')
            return render_template('admin/menu/form.html', menu=menu, edit=True)
        
        # Update menu item
        menu.name = name
        menu.description = description
        menu.price = price
        menu.category = category if category else None
        menu.is_active = is_active
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                try:
                    # Delete old image file
                    delete_menu_image(menu.image_url)
                    
                    menu.image_url = save_menu_image(file)
                except ValueError as e:
                    flash(str(e), 'error')
                    return render_template('admin/menu/form.html', menu=menu, edit=True)
        
        db.session.commit()
        
        flash(f'แก้ไขเมนู "{name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin.menu_list'))
    
    return render_template('admin/menu/form.html', menu=menu, edit=True)


@admin_bp.route('/menu/<int:menu_id>/delete', methods=['POST'])
@admin_required
def menu_delete(menu_id):
    """Delete menu item"""
    menu = Menu.query.get_or_404(menu_id)
    
    # Check if menu is used in any active orders
    from models import OrderItem
    active_orders = OrderItem.query.join(Menu).filter(
        Menu.id == menu_id,
        OrderItem.order.has(status__in=['pending', 'accepted', 'preparing', 'ready', 'delivering'])
    ).first()
    
    if active_orders:
        flash('ไม่สามารถลบเมนูที่มีการสั่งซื้ออยู่', 'error')
        return redirect(url_for('admin.menu_list'))
    
    menu_name = menu.name
    db.session.delete(menu)
    db.session.commit()
    
    # Delete menu image file
    delete_menu_image(menu.image_url)
    
    flash(f'ลบเมนู "{menu_name}" เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.menu_list'))


@admin_bp.route('/menu/<int:menu_id>')
@admin_required
def menu_detail(menu_id):
    """View menu item details"""
    menu = Menu.query.get_or_404(menu_id)
    
    # Get recipe BOM if exists
    from models import RecipeBOM
    recipe_items = RecipeBOM.query.filter_by(menu_id=menu_id, is_active=True).all()
    
    return render_template('admin/menu/detail.html', menu=menu, recipe_items=recipe_items)


@admin_bp.route('/menu/<int:menu_id>/options')
@admin_required
def menu_options(menu_id):
    """Manage menu options"""
    menu = Menu.query.get_or_404(menu_id)
    option_groups = MenuOptionGroup.query.filter_by(menu_id=menu_id, is_active=True).all()
    
    return render_template('admin/menu/options.html', menu=menu, option_groups=option_groups)


@admin_bp.route('/menu/<int:menu_id>/options/create', methods=['POST'])
@admin_required
def menu_option_group_create(menu_id):
    """Create new option group"""
    menu = Menu.query.get_or_404(menu_id)
    
    name = request.form.get('name', '').strip()
    is_required = request.form.get('is_required') == 'on'
    is_multiple = request.form.get('is_multiple') == 'on'
    
    if not name:
        flash('กรุณากรอกชื่อกลุ่มตัวเลือก', 'error')
        return redirect(url_for('admin.menu_options', menu_id=menu_id))
    
    option_group = MenuOptionGroup(
        menu_id=menu_id,
        name=name,
        is_required=is_required,
        is_multiple=is_multiple
    )
    
    db.session.add(option_group)
    db.session.commit()
    
    flash(f'เพิ่มกลุ่มตัวเลือก "{name}" เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.menu_options', menu_id=menu_id))


@admin_bp.route('/api/menu/<int:menu_id>/toggle-status', methods=['POST'])
@admin_required
def api_menu_toggle_status(menu_id):
    """Toggle menu active status"""
    menu = Menu.query.get_or_404(menu_id)
    menu.is_active = not menu.is_active
    db.session.commit()
    
    status = 'เปิดขาย' if menu.is_active else 'ปิดขาย'
    return jsonify({
        'success': True,
        'message': f'เปลี่ยนสถานะเมนู "{menu.name}" เป็น {status}',
        'is_active': menu.is_active
    })


@admin_bp.route('/api/menu/bulk-update', methods=['POST'])
@admin_required
def api_menu_bulk_update():
    """Bulk update menu status"""
    try:
        data = request.get_json()
        menu_ids = data.get('menu_ids', [])
        is_active = data.get('is_active', True)
        
        if not menu_ids:
            return jsonify({'error': 'ไม่มีเมนูที่เลือก'}), 400
        
        # Update multiple menus
        updated_count = Menu.query.filter(Menu.id.in_(menu_ids)).update(
            {Menu.is_active: is_active}, 
            synchronize_session=False
        )
        
        db.session.commit()
        
        status_text = 'เปิดใช้งาน' if is_active else 'ปิดใช้งาน'
        return jsonify({
            'success': True,
            'message': f'{status_text}เมนู {updated_count} รายการเรียบร้อยแล้ว',
            'updated_count': updated_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500


@admin_bp.route('/api/menu/bulk-delete', methods=['POST'])
@admin_required
def api_menu_bulk_delete():
    """Bulk delete menus"""
    try:
        data = request.get_json()
        menu_ids = data.get('menu_ids', [])
        
        if not menu_ids:
            return jsonify({'error': 'ไม่มีเมนูที่เลือก'}), 400
        
        # Check for active orders
        from models import OrderItem
        active_orders = OrderItem.query.join(Menu).filter(
            Menu.id.in_(menu_ids),
            OrderItem.order.has(status__in=['pending', 'accepted', 'preparing', 'ready', 'delivering'])
        ).first()
        
        if active_orders:
            return jsonify({'error': 'ไม่สามารถลบเมนูที่มีการสั่งซื้ออยู่'}), 400
        
        # Delete menus
        deleted_count = Menu.query.filter(Menu.id.in_(menu_ids)).delete(
            synchronize_session=False
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'ลบเมนู {deleted_count} รายการเรียบร้อยแล้ว',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500


@admin_bp.route('/api/menu/<int:menu_id>', methods=['PATCH'])
@admin_required
def api_menu_update(menu_id):
    """Update single menu via API"""
    try:
        menu = Menu.query.get_or_404(menu_id)
        data = request.get_json()
        
        # Update fields
        if 'is_active' in data:
            menu.is_active = data['is_active']
        
        if 'name' in data:
            menu.name = data['name']
            
        if 'price' in data:
            menu.price = float(data['price'])
            
        if 'category' in data:
            menu.category = data['category']
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'อัปเดตเมนู "{menu.name}" เรียบร้อยแล้ว',
            'menu': {
                'id': menu.id,
                'name': menu.name,
                'price': float(menu.price),
                'is_active': menu.is_active,
                'category': menu.category
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500
