"""
Admin Authentication Routes
Phase 2 - Admin Login and Session Management

Handles admin user authentication and authorization.
"""

from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from models import User, db
from . import admin_bp


def admin_required(f):
    """Decorator to require admin role for route access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบก่อน', 'error')
            return redirect(url_for('admin.login'))
        
        if current_user.role != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน', 'error')
            return render_template('admin/login.html')
        
        # Find admin user
        user = User.query.filter_by(username=username, role='admin').first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            user.update_last_login()
            
            flash(f'ยินดีต้อนรับ {user.username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    
    return render_template('admin/login.html')


@admin_bp.route('/logout')
@login_required
def logout():
    """Admin logout"""
    logout_user()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('admin.login'))


@admin_bp.route('/profile')
@admin_required
def profile():
    """Admin profile page"""
    from datetime import datetime
    
    # Mock settings data - in real app this would come from database
    settings = {
        'vat_rate': 7,
        'service_charge': 10,
        'prep_time': 20,
        'min_order': 100
    }
    
    return render_template('admin/profile.html', 
                         settings=settings, 
                         today=datetime.now())


@admin_bp.route('/change-password', methods=['POST'])
@admin_required
def change_password():
    """Change admin password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'error')
        return redirect(url_for('admin.profile'))
    
    if not current_user.check_password(current_password):
        flash('รหัสผ่านปัจจุบันไม่ถูกต้อง', 'error')
        return redirect(url_for('admin.profile'))
    
    if new_password != confirm_password:
        flash('รหัสผ่านใหม่ไม่ตรงกัน', 'error')
        return redirect(url_for('admin.profile'))
    
    if len(new_password) < 6:
        flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
        return redirect(url_for('admin.profile'))
    
    # Update password
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('เปลี่ยนรหัสผ่านเรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.profile'))
