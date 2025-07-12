"""
LanAim POS System v5.3 - User Management Routes
Admin interface for managing staff users and permissions
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, get_thai_now
from security import admin_required
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Create blueprint
user_management_bp = Blueprint('user_management', __name__)

def super_admin_required(f):
    """Decorator for super admin only functions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึงฟังก์ชันนี้', 'error')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@user_management_bp.route('/admin/users')
@login_required
@admin_required
def user_list():
    """Display list of all users"""
    try:
        # Get filter parameters
        role_filter = request.args.get('role', '')
        status_filter = request.args.get('status', '')
        search = request.args.get('search', '')
        
        # Build query
        query = User.query
        
        if role_filter:
            query = query.filter(User.role == role_filter)
            
        if status_filter == 'active':
            query = query.filter(User.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(User.is_active == False)
            
        if search:
            query = query.filter(User.username.contains(search))
            
        users = query.order_by(User.created_at.desc()).all()
        
        # Get summary statistics
        total_users = User.query.count()
        active_users = User.query.filter(User.is_active == True).count()
        admin_count = User.query.filter(User.role == 'admin').count()
        kitchen_count = User.query.filter(User.role == 'kitchen_staff').count()
        delivery_count = User.query.filter(User.role == 'delivery_staff').count()
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'admin_count': admin_count,
            'kitchen_count': kitchen_count,
            'delivery_count': delivery_count
        }
        
        # Available roles for filter dropdown
        roles = ['admin', 'kitchen_staff', 'delivery_staff']
        
        return render_template('admin/users/list.html', 
                             users=users, 
                             stats=stats, 
                             roles=roles,
                             current_role_filter=role_filter,
                             current_status_filter=status_filter,
                             current_search=search)
                             
    except Exception as e:
        logger.error(f"Error in user_list: {str(e)}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ใช้', 'error')
        return redirect(url_for('admin.dashboard'))

@user_management_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@super_admin_required
def user_create():
    """Create new user"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            role = request.form.get('role', '')
            email = request.form.get('email', '').strip()
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            is_active = bool(request.form.get('is_active'))
            
            # Validation
            if not username:
                flash('กรุณากรอกชื่อผู้ใช้', 'error')
                return render_template('admin/users/form.html', edit=False)
                
            if User.query.filter_by(username=username).first():
                flash('ชื่อผู้ใช้นี้มีอยู่แล้ว', 'error')
                return render_template('admin/users/form.html', edit=False)
                
            if not password:
                flash('กรุณากรอกรหัสผ่าน', 'error')
                return render_template('admin/users/form.html', edit=False)
                
            if password != confirm_password:
                flash('รหัสผ่านไม่ตรงกัน', 'error')
                return render_template('admin/users/form.html', edit=False)
                
            if len(password) < 6:
                flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
                return render_template('admin/users/form.html', edit=False)
                
            if role not in ['admin', 'kitchen_staff', 'delivery_staff']:
                flash('กรุณาเลือกตำแหน่งที่ถูกต้อง', 'error')
                return render_template('admin/users/form.html', edit=False)
                
            # Create new user
            new_user = User(
                username=username,
                role=role,
                email=email if email else None,
                full_name=full_name if full_name else None,
                phone=phone if phone else None,
                is_active=is_active,
                created_at=get_thai_now()
            )
            
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"User created: {username} by {current_user.username}")
            flash(f'สร้างผู้ใช้ {username} สำเร็จ', 'success')
            return redirect(url_for('user_management.user_list'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash('เกิดข้อผิดพลาดในการสร้างผู้ใช้', 'error')
            
    return render_template('admin/users/form.html', edit=False)

@user_management_bp.route('/admin/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """Display user details"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Get user statistics (if applicable)
        stats = {
            'login_count': getattr(user, 'login_count', 0),
            'last_login': user.last_login,
            'created_at': user.created_at,
            'orders_handled': 0,  # This would need to be calculated based on your order tracking
        }
        
        return render_template('admin/users/detail.html', user=user, stats=stats)
        
    except Exception as e:
        logger.error(f"Error in user_detail: {str(e)}")
        flash('ไม่พบผู้ใช้ที่ระบุ', 'error')
        return redirect(url_for('user_management.user_list'))

@user_management_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def user_edit(user_id):
    """Edit user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent editing super admin
        if user.username == 'admin' and current_user.id != user.id:
            flash('ไม่สามารถแก้ไขบัญชีผู้ดูแลระบบได้', 'error')
            return redirect(url_for('user_management.user_list'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            role = request.form.get('role', '')
            email = request.form.get('email', '').strip()
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            is_active = bool(request.form.get('is_active'))
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username:
                flash('กรุณากรอกชื่อผู้ใช้', 'error')
                return render_template('admin/users/form.html', user=user, edit=True)
                
            if username != user.username and User.query.filter_by(username=username).first():
                flash('ชื่อผู้ใช้นี้มีอยู่แล้ว', 'error')
                return render_template('admin/users/form.html', user=user, edit=True)
                
            if role not in ['admin', 'kitchen_staff', 'delivery_staff']:
                flash('กรุณาเลือกตำแหน่งที่ถูกต้อง', 'error')
                return render_template('admin/users/form.html', user=user, edit=True)
                
            # Check password if provided
            if new_password:
                if new_password != confirm_password:
                    flash('รหัสผ่านใหม่ไม่ตรงกัน', 'error')
                    return render_template('admin/users/form.html', user=user, edit=True)
                    
                if len(new_password) < 6:
                    flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
                    return render_template('admin/users/form.html', user=user, edit=True)
            
            # Update user
            user.username = username
            user.role = role
            user.email = email if email else None
            user.full_name = full_name if full_name else None
            user.phone = phone if phone else None
            user.is_active = is_active
            user.updated_at = get_thai_now()
            
            if new_password:
                user.set_password(new_password)
                
            db.session.commit()
            
            logger.info(f"User updated: {username} by {current_user.username}")
            flash(f'อัปเดตผู้ใช้ {username} สำเร็จ', 'success')
            return redirect(url_for('user_management.user_detail', user_id=user.id))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user: {str(e)}")
        flash('เกิดข้อผิดพลาดในการอัปเดตผู้ใช้', 'error')
        
    return render_template('admin/users/form.html', user=user, edit=True)

@user_management_bp.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@super_admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deactivating super admin
        if user.username == 'admin':
            return jsonify({'success': False, 'error': 'ไม่สามารถปิดใช้งานบัญชีผู้ดูแลระบบได้'})
            
        user.is_active = not user.is_active
        user.updated_at = get_thai_now()
        
        db.session.commit()
        
        status_text = 'เปิดใช้งาน' if user.is_active else 'ปิดใช้งาน'
        logger.info(f"User status toggled: {user.username} -> {status_text} by {current_user.username}")
        
        return jsonify({
            'success': True, 
            'is_active': user.is_active,
            'message': f'{status_text}ผู้ใช้ {user.username} สำเร็จ'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling user status: {str(e)}")
        return jsonify({'success': False, 'error': 'เกิดข้อผิดพลาดในการเปลี่ยนสถานะ'})

@user_management_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def user_delete(user_id):
    """Delete user (soft delete by deactivating)"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting super admin
        if user.username == 'admin':
            flash('ไม่สามารถลบบัญชีผู้ดูแลระบบได้', 'error')
            return redirect(url_for('user_management.user_list'))
            
        # Soft delete by deactivating
        user.is_active = False
        user.updated_at = get_thai_now()
        
        db.session.commit()
        
        logger.info(f"User soft deleted: {user.username} by {current_user.username}")
        flash(f'ลบผู้ใช้ {user.username} สำเร็จ', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        flash('เกิดข้อผิดพลาดในการลบผู้ใช้', 'error')
        
    return redirect(url_for('user_management.user_list'))

@user_management_bp.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@super_admin_required
def reset_user_password(user_id):
    """Reset user password to default"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Generate default password (username + 123)
        default_password = f"{user.username}123"
        user.set_password(default_password)
        user.updated_at = get_thai_now()
        
        db.session.commit()
        
        logger.info(f"Password reset for user: {user.username} by {current_user.username}")
        flash(f'รีเซ็ตรหัสผ่านของ {user.username} สำเร็จ (รหัสผ่านใหม่: {default_password})', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting password: {str(e)}")
        flash('เกิดข้อผิดพลาดในการรีเซ็ตรหัสผ่าน', 'error')
        
    return redirect(url_for('user_management.user_detail', user_id=user_id))

# API endpoints for AJAX operations
@user_management_bp.route('/admin/api/users/<int:user_id>/status', methods=['PATCH'])
@login_required
@super_admin_required
def api_toggle_user_status(user_id):
    """API endpoint to toggle user status"""
    return toggle_user_status(user_id)