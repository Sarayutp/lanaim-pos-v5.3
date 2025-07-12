"""
LanAim POS System v5.3 - Settings Management Routes
Admin interface for managing system settings and configuration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Setting, get_thai_now
from security import admin_required
from functools import wraps
import logging
import json

logger = logging.getLogger(__name__)

# Create blueprint
settings_management_bp = Blueprint('settings_management', __name__)

# Default settings configuration
DEFAULT_SETTINGS = {
    'general': {
        'restaurant_name': {
            'value': 'ร้านลานอิ่ม',
            'description': 'ชื่อร้านอาหาร',
            'data_type': 'string'
        },
        'restaurant_phone': {
            'value': '02-123-4567',
            'description': 'เบอร์โทรศัพท์ร้าน',
            'data_type': 'string'
        },
        'restaurant_address': {
            'value': '123 ถนนสุขุมวิท กรุงเทพฯ 10110',
            'description': 'ที่อยู่ร้าน',
            'data_type': 'string'
        },
        'restaurant_email': {
            'value': 'info@lanaim.com',
            'description': 'อีเมลร้าน',
            'data_type': 'string'
        },
        'business_hours': {
            'value': '{"monday": {"open": "09:00", "close": "22:00"}, "tuesday": {"open": "09:00", "close": "22:00"}, "wednesday": {"open": "09:00", "close": "22:00"}, "thursday": {"open": "09:00", "close": "22:00"}, "friday": {"open": "09:00", "close": "22:00"}, "saturday": {"open": "09:00", "close": "23:00"}, "sunday": {"open": "09:00", "close": "23:00"}}',
            'description': 'เวลาทำการ',
            'data_type': 'json'
        },
        'timezone': {
            'value': 'Asia/Bangkok',
            'description': 'เขตเวลา',
            'data_type': 'string'
        },
        'currency': {
            'value': 'THB',
            'description': 'สกุลเงิน',
            'data_type': 'string'
        },
        'language': {
            'value': 'th',
            'description': 'ภาษาหลัก',
            'data_type': 'string'
        }
    },
    'ordering': {
        'allow_online_ordering': {
            'value': 'true',
            'description': 'อนุญาตสั่งอาหารออนไลน์',
            'data_type': 'boolean'
        },
        'min_order_amount': {
            'value': '100',
            'description': 'ยอดสั่งซื้อขั้นต่ำ (บาท)',
            'data_type': 'float'
        },
        'order_timeout_minutes': {
            'value': '30',
            'description': 'เวลาหมดอายุของออเดอร์ (นาที)',
            'data_type': 'integer'
        },
        'auto_accept_orders': {
            'value': 'false',
            'description': 'รับออเดอร์อัตโนมัติ',
            'data_type': 'boolean'
        },
        'max_items_per_order': {
            'value': '50',
            'description': 'จำนวนรายการสูงสุดต่อออเดอร์',
            'data_type': 'integer'
        }
    },
    'payment': {
        'accept_cash': {
            'value': 'true',
            'description': 'รับชำระเงินสด',
            'data_type': 'boolean'
        },
        'accept_bank_transfer': {
            'value': 'true',
            'description': 'รับโอนเงินผ่านธนาคาร',
            'data_type': 'boolean'
        },
        'accept_promptpay': {
            'value': 'true',
            'description': 'รับชำระผ่าน PromptPay',
            'data_type': 'boolean'
        },
        'promptpay_id': {
            'value': '0123456789',
            'description': 'หมายเลข PromptPay',
            'data_type': 'string'
        },
        'bank_account_name': {
            'value': 'ร้านลานอิ่ม',
            'description': 'ชื่อบัญชีธนาคาร',
            'data_type': 'string'
        },
        'bank_account_number': {
            'value': '123-4-56789-0',
            'description': 'เลขบัญชีธนาคาร',
            'data_type': 'string'
        },
        'bank_name': {
            'value': 'ธนาคารกสิกรไทย',
            'description': 'ชื่อธนาคาร',
            'data_type': 'string'
        }
    },
    'delivery': {
        'enable_delivery': {
            'value': 'true',
            'description': 'เปิดบริการส่งอาหาร',
            'data_type': 'boolean'
        },
        'delivery_fee': {
            'value': '30',
            'description': 'ค่าส่งพื้นฐาน (บาท)',
            'data_type': 'float'
        },
        'free_delivery_threshold': {
            'value': '500',
            'description': 'ยอดขั้นต่ำสำหรับส่งฟรี (บาท)',
            'data_type': 'float'
        },
        'max_delivery_distance': {
            'value': '10',
            'description': 'ระยะทางส่งสูงสุด (กิโลเมตร)',
            'data_type': 'float'
        },
        'estimated_delivery_time': {
            'value': '45',
            'description': 'เวลาส่งโดยประมาณ (นาที)',
            'data_type': 'integer'
        }
    },
    'notifications': {
        'email_notifications': {
            'value': 'true',
            'description': 'ส่งการแจ้งเตือนทางอีเมล',
            'data_type': 'boolean'
        },
        'sms_notifications': {
            'value': 'false',
            'description': 'ส่งการแจ้งเตือนทาง SMS',
            'data_type': 'boolean'
        },
        'line_notifications': {
            'value': 'false',
            'description': 'ส่งการแจ้งเตือนทาง LINE',
            'data_type': 'boolean'
        },
        'admin_notification_email': {
            'value': 'admin@lanaim.com',
            'description': 'อีเมลสำหรับแจ้งเตือนผู้ดูแล',
            'data_type': 'string'
        }
    },
    'kitchen': {
        'auto_print_orders': {
            'value': 'true',
            'description': 'พิมพ์ออเดอร์อัตโนมัติ',
            'data_type': 'boolean'
        },
        'kitchen_display_timeout': {
            'value': '120',
            'description': 'เวลาแสดงออเดอร์บนหน้าจอครัว (วินาที)',
            'data_type': 'integer'
        },
        'max_concurrent_orders': {
            'value': '20',
            'description': 'จำนวนออเดอร์สูงสุดที่ทำพร้อมกัน',
            'data_type': 'integer'
        }
    }
}

def super_admin_required(f):
    """Decorator for super admin only functions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึงฟังก์ชันนี้', 'error')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@settings_management_bp.route('/admin/settings')
@login_required
@super_admin_required
def settings_list():
    """Display settings by category"""
    try:
        # Get selected category from query parameter
        selected_category = request.args.get('category', 'general')
        
        # Get all available categories
        categories = db.session.query(Setting.category).distinct().all()
        available_categories = [cat[0] for cat in categories]
        
        # If no settings exist, initialize with defaults
        if not available_categories:
            initialize_default_settings()
            available_categories = list(DEFAULT_SETTINGS.keys())
        
        # Ensure selected category is valid
        if selected_category not in available_categories:
            selected_category = available_categories[0] if available_categories else 'general'
        
        # Get settings for selected category
        settings = Setting.get_by_category(selected_category)
        
        # Get category statistics
        stats = {}
        for category in available_categories:
            count = Setting.query.filter_by(category=category).count()
            stats[category] = count
        
        return render_template('admin/settings/list.html',
                             settings=settings,
                             categories=available_categories,
                             selected_category=selected_category,
                             stats=stats)
                             
    except Exception as e:
        logger.error(f"Error in settings_list: {str(e)}")
        flash('เกิดข้อผิดพลาดในการโหลดการตั้งค่า', 'error')
        return redirect(url_for('admin.dashboard'))

@settings_management_bp.route('/admin/settings/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def settings_edit():
    """Edit settings by category"""
    if request.method == 'POST':
        try:
            category = request.form.get('category', 'general')
            
            # Get all settings for this category
            settings = Setting.get_by_category(category)
            
            # Update each setting
            updated_count = 0
            for setting in settings:
                new_value = request.form.get(f'setting_{setting.id}')
                if new_value is not None:
                    # Handle different data types
                    if setting.data_type == 'boolean':
                        # Checkbox values
                        new_value = request.form.get(f'setting_{setting.id}') == 'on'
                    
                    # Set the value using the model's method
                    setting.set_value(new_value)
                    setting.updated_by = current_user.id
                    setting.updated_at = get_thai_now()
                    updated_count += 1
            
            db.session.commit()
            
            logger.info(f"Settings updated in category '{category}' by {current_user.username}")
            flash(f'อัปเดตการตั้งค่า {updated_count} รายการในหมวด {category} สำเร็จ', 'success')
            return redirect(url_for('settings_management.settings_list', category=category))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating settings: {str(e)}")
            flash('เกิดข้อผิดพลาดในการอัปเดตการตั้งค่า', 'error')
    
    # GET request - show edit form
    category = request.args.get('category', 'general')
    settings = Setting.get_by_category(category)
    
    return render_template('admin/settings/edit.html',
                         settings=settings,
                         category=category)

@settings_management_bp.route('/admin/settings/add', methods=['GET', 'POST'])
@login_required
@super_admin_required
def settings_add():
    """Add new setting"""
    if request.method == 'POST':
        try:
            key = request.form.get('key', '').strip()
            value = request.form.get('value', '').strip()
            category = request.form.get('category', '').strip()
            description = request.form.get('description', '').strip()
            data_type = request.form.get('data_type', 'string')
            is_public = request.form.get('is_public') == 'on'
            
            # Validation
            if not key:
                flash('กรุณากรอกชื่อการตั้งค่า', 'error')
                return render_template('admin/settings/form.html')
            
            if not category:
                flash('กรุณากรอกหมวดหมู่', 'error')
                return render_template('admin/settings/form.html')
            
            # Check if key already exists
            if Setting.query.filter_by(key=key).first():
                flash('ชื่อการตั้งค่านี้มีอยู่แล้ว', 'error')
                return render_template('admin/settings/form.html')
            
            # Create new setting
            setting = Setting(
                key=key,
                category=category,
                description=description,
                data_type=data_type,
                is_public=is_public,
                updated_by=current_user.id
            )
            
            setting.set_value(value)
            
            db.session.add(setting)
            db.session.commit()
            
            logger.info(f"Setting created: {key} by {current_user.username}")
            flash(f'เพิ่มการตั้งค่า "{key}" สำเร็จ', 'success')
            return redirect(url_for('settings_management.settings_list', category=category))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating setting: {str(e)}")
            flash('เกิดข้อผิดพลาดในการเพิ่มการตั้งค่า', 'error')
    
    return render_template('admin/settings/form.html')

@settings_management_bp.route('/admin/settings/<int:setting_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def settings_delete(setting_id):
    """Delete setting"""
    try:
        setting = Setting.query.get_or_404(setting_id)
        category = setting.category
        key = setting.key
        
        db.session.delete(setting)
        db.session.commit()
        
        logger.info(f"Setting deleted: {key} by {current_user.username}")
        flash(f'ลบการตั้งค่า "{key}" สำเร็จ', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting setting: {str(e)}")
        flash('เกิดข้อผิดพลาดในการลบการตั้งค่า', 'error')
        category = 'general'
    
    return redirect(url_for('settings_management.settings_list', category=category))

@settings_management_bp.route('/admin/settings/reset/<category>', methods=['POST'])
@login_required
@super_admin_required
def settings_reset_category(category):
    """Reset settings in a category to defaults"""
    try:
        if category not in DEFAULT_SETTINGS:
            flash('ไม่พบหมวดหมู่ที่ระบุ', 'error')
            return redirect(url_for('settings_management.settings_list'))
        
        # Delete existing settings in category
        Setting.query.filter_by(category=category).delete()
        
        # Add default settings for category
        for key, config in DEFAULT_SETTINGS[category].items():
            setting = Setting(
                key=key,
                category=category,
                description=config['description'],
                data_type=config['data_type'],
                updated_by=current_user.id
            )
            setting.set_value(config['value'])
            db.session.add(setting)
        
        db.session.commit()
        
        logger.info(f"Settings reset for category '{category}' by {current_user.username}")
        flash(f'รีเซ็ตการตั้งค่าหมวด {category} เป็นค่าเริ่มต้นสำเร็จ', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting settings: {str(e)}")
        flash('เกิดข้อผิดพลาดในการรีเซ็ตการตั้งค่า', 'error')
    
    return redirect(url_for('settings_management.settings_list', category=category))

@settings_management_bp.route('/admin/api/settings/initialize', methods=['POST'])
@login_required
@super_admin_required
def api_initialize_settings():
    """Initialize default settings"""
    try:
        initialize_default_settings()
        return jsonify({
            'success': True,
            'message': 'เริ่มต้นการตั้งค่าเริ่มต้นสำเร็จ'
        })
    except Exception as e:
        logger.error(f"Error initializing settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'เกิดข้อผิดพลาดในการเริ่มต้นการตั้งค่า'
        }), 500

def initialize_default_settings():
    """Initialize default settings if they don't exist"""
    for category, settings in DEFAULT_SETTINGS.items():
        for key, config in settings.items():
            # Check if setting already exists
            if not Setting.query.filter_by(key=key).first():
                setting = Setting(
                    key=key,
                    category=category,
                    description=config['description'],
                    data_type=config['data_type']
                )
                setting.set_value(config['value'])
                db.session.add(setting)
    
    db.session.commit()
    logger.info("Default settings initialized")