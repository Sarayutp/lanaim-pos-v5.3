"""
LanAim POS System v2.4 - Phase 1
Data Models for Core Ordering Loop

This module contains all SQLAlchemy models for the LanAim POS system.
Models are designed to support the core ordering workflow from customer
order placement to staff order fulfillment.
"""

from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()

# Thai timezone for consistent datetime handling
THAI_TZ = timezone(timedelta(hours=7))

def get_thai_now():
    """Get current time in Thai timezone"""
    return datetime.now(THAI_TZ)

def init_db(app):
    """Initialize database with Flask app"""
    if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
        db.init_app(app)

class User(UserMixin, db.Model):
    """
    User model for staff authentication
    Supports admin, kitchen_staff and delivery_staff roles
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'kitchen_staff' or 'delivery_staff'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = get_thai_now()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class DeliveryZone(db.Model):
    """
    Delivery zones/tables for order placement
    Represents physical locations where customers can order from
    """
    __tablename__ = 'delivery_zones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "โต๊ะ 1", "โซน A"
    description = db.Column(db.Text)  # Additional details about the zone
    delivery_fee = db.Column(db.Float, default=0.0, nullable=False)  # Delivery fee for this zone
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    # Relationship
    orders = db.relationship('Order', backref='delivery_zone', lazy=True)
    
    def __repr__(self):
        return f'<DeliveryZone {self.name}>'
    
    def __repr__(self):
        return f'<DeliveryZone {self.name}>'

class Menu(db.Model):
    """
    Menu items available for ordering
    Core menu structure with pricing and availability
    """
    __tablename__ = 'menus'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Base price
    image_url = db.Column(db.String(255))  # Path to menu image
    category = db.Column(db.String(50))  # e.g., "อาหารจานเดียว", "เครื่องดื่ม"
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    
    # Relationships
    option_groups = db.relationship('MenuOptionGroup', backref='menu', lazy=True, cascade='all, delete-orphan')
    
    def get_base_price(self):
        """Get base price as float"""
        return float(self.price)
    
    def __repr__(self):
        return f'<Menu {self.name} - ฿{self.price}>'

class MenuOptionGroup(db.Model):
    """
    Option groups for menu customization
    e.g., "เพิ่มท็อปปิ้ง", "ระดับความเผ็ด"
    """
    __tablename__ = 'menu_option_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., "เพิ่มท็อปปิ้ง"
    is_required = db.Column(db.Boolean, default=False)  # Must select an option
    max_selections = db.Column(db.Integer, default=1)  # Maximum options selectable
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    # Relationships
    options = db.relationship('MenuOptionItem', backref='group', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<MenuOptionGroup {self.name}>'

class MenuOptionItem(db.Model):
    """
    Individual options within option groups
    e.g., "ไข่ดาว (+10 บาท)", "ชีส (+15 บาท)"
    """
    __tablename__ = 'menu_option_items'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('menu_option_groups.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., "ไข่ดาว"
    additional_price = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    def get_additional_price(self):
        """Get additional price as float"""
        return float(self.additional_price)
    
    def __repr__(self):
        return f'<MenuOptionItem {self.name} (+฿{self.additional_price})>'

class Order(db.Model):
    """
    Customer orders - central entity of the ordering system
    Tracks complete order lifecycle from placement to completion
    """
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Customer information
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    delivery_address_details = db.Column(db.Text, nullable=False)
    delivery_zone_id = db.Column(db.Integer, db.ForeignKey('delivery_zones.id'), nullable=True)
    
    # Order financial details
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Order status tracking
    status = db.Column(db.String(20), default='pending', nullable=False)
    # Status flow: pending -> accepted -> preparing -> ready -> delivered -> completed
    # Can also be: cancelled
    
    # Payment information
    payment_method = db.Column(db.String(10), nullable=False)  # 'COD' or 'TOD'
    payment_status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending' or 'paid'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    last_updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    accepted_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Staff handling
    accepted_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    delivered_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', backref='order', lazy=True, uselist=False)
    accepted_by = db.relationship('User', foreign_keys=[accepted_by_user_id], backref='accepted_orders')
    delivered_by = db.relationship('User', foreign_keys=[delivered_by_user_id], backref='delivered_orders')
    
    def generate_order_number(self):
        """Generate unique order number with Thai date format"""
        now = get_thai_now()
        date_str = now.strftime('%Y%m%d')
        # Format: LA20250711-001
        base_number = f"LA{date_str}-"
        
        # Find the highest number for today
        today_orders = Order.query.filter(
            Order.order_number.like(f"{base_number}%")
        ).count()
        
        sequence = str(today_orders + 1).zfill(3)
        self.order_number = f"{base_number}{sequence}"
    
    def get_total_price(self):
        """Get total price as float"""
        return float(self.total_price)
    
    def update_status(self, new_status, user=None):
        """Update order status with timestamp tracking"""
        self.status = new_status
        self.last_updated_at = get_thai_now()
        
        if new_status == 'accepted' and user:
            self.accepted_at = get_thai_now()
            self.accepted_by_user_id = user.id
        elif new_status == 'delivered':
            # Mark payment as completed when order is delivered
            self.completed_at = get_thai_now()
            self.payment_status = 'paid'
            if user and user.role == 'delivery_staff':
                self.delivered_by_user_id = user.id
        elif new_status == 'completed':
            self.completed_at = get_thai_now()
            self.payment_status = 'paid'
            if user and user.role == 'delivery_staff':
                self.delivered_by_user_id = user.id
    
    def can_be_cancelled(self):
        """Check if order can be cancelled (before acceptance)"""
        return self.status == 'pending'
    
    def can_be_modified(self):
        """Check if order can be modified (before acceptance)"""
        return self.status == 'pending'
    
    def get_status_display(self):
        """Get Thai display text for status"""
        status_map = {
            'pending': 'รอรับออเดอร์',
            'accepted': 'รับออเดอร์แล้ว',
            'preparing': 'กำลังเตรียม',
            'ready': 'พร้อมส่ง',
            'delivered': 'จัดส่งแล้ว',
            'completed': 'เสร็จสิ้น',
            'cancelled': 'ยกเลิก'
        }
        return status_map.get(self.status, self.status)
    
    def __repr__(self):
        return f'<Order {self.order_number} - {self.customer_name}>'

class OrderItem(db.Model):
    """
    Individual items within an order
    Stores snapshot of menu item details at time of order
    """
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    
    # Snapshot of menu item at time of order (prevents issues with price changes)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    menu_name = db.Column(db.String(100), nullable=False)
    price_per_item = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    # Special requests/notes
    special_requests = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    # Relationships
    options = db.relationship('OrderItemOption', backref='order_item', lazy=True, cascade='all, delete-orphan')
    menu_ref = db.relationship('Menu', backref='order_items')
    
    def get_total_price(self):
        """Calculate total price including options"""
        base_total = float(self.price_per_item) * self.quantity
        options_total = sum(float(option.option_price) * self.quantity for option in self.options)
        return base_total + options_total
    
    def __repr__(self):
        return f'<OrderItem {self.menu_name} x{self.quantity}>'

class OrderItemOption(db.Model):
    """
    Selected options for order items
    Stores snapshot of option details at time of order
    """
    __tablename__ = 'order_item_options'
    
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=False)
    
    # Snapshot of option at time of order
    option_id = db.Column(db.Integer, db.ForeignKey('menu_option_items.id'), nullable=False)
    option_name = db.Column(db.String(100), nullable=False)
    option_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    # Relationships
    option_ref = db.relationship('MenuOptionItem', backref='order_selections')
    
    def __repr__(self):
        return f'<OrderItemOption {self.option_name} +฿{self.option_price}>'

class Feedback(db.Model):
    """
    Customer feedback and ratings for completed orders
    Helps track customer satisfaction
    """
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    def __repr__(self):
        return f'<Feedback {self.rating}⭐ for Order {self.order_id}>'

# =============================================================================
# PHASE 2 MODELS - Admin & Operational Management
# =============================================================================

class Ingredient(db.Model):
    """
    Ingredient/Raw material management
    Tracks stock quantities and low stock alerts
    """
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    stock_quantity = db.Column(db.Numeric(10, 3), default=0, nullable=False)  # Current stock
    unit = db.Column(db.String(20), nullable=False)  # e.g., "kg", "กิโลกรัม", "ชิ้น"
    low_stock_threshold = db.Column(db.Numeric(10, 3), default=0, nullable=False)  # Alert threshold
    cost_per_unit = db.Column(db.Numeric(10, 2), default=0)  # Cost for inventory calculation
    supplier = db.Column(db.String(100))  # Supplier information
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    
    # Relationships
    recipe_items = db.relationship('RecipeBOM', backref='ingredient', lazy=True)
    stock_adjustments = db.relationship('StockAdjustment', backref='ingredient', lazy=True)
    
    def is_low_stock(self):
        """Check if ingredient is below low stock threshold"""
        return float(self.stock_quantity) <= float(self.low_stock_threshold)
    
    def add_stock(self, quantity, user_id, notes=None):
        """Add stock and create adjustment record"""
        self.stock_quantity += quantity
        self.updated_at = get_thai_now()
        
        # Create stock adjustment record
        adjustment = StockAdjustment(
            ingredient_id=self.id,
            type='in',
            quantity=quantity,
            adjusted_by=user_id,
            notes=notes or f"Stock added: {quantity} {self.unit}"
        )
        db.session.add(adjustment)
        db.session.commit()
    
    def deduct_stock(self, quantity, user_id, notes=None):
        """Deduct stock and create adjustment record"""
        if float(self.stock_quantity) >= float(quantity):
            self.stock_quantity -= quantity
            self.updated_at = get_thai_now()
            
            # Create stock adjustment record
            adjustment = StockAdjustment(
                ingredient_id=self.id,
                type='out',
                quantity=quantity,
                adjusted_by=user_id,
                notes=notes or f"Stock deducted: {quantity} {self.unit}"
            )
            db.session.add(adjustment)
            db.session.commit()
            return True
        return False
    
    def adjust_stock(self, new_quantity, user_id, notes=None):
        """Manually adjust stock to specific quantity"""
        old_quantity = float(self.stock_quantity)
        self.stock_quantity = new_quantity
        self.updated_at = get_thai_now()
        
        # Create stock adjustment record
        adjustment = StockAdjustment(
            ingredient_id=self.id,
            type='correction',
            quantity=new_quantity - old_quantity,
            adjusted_by=user_id,
            notes=notes or f"Stock correction: {old_quantity} → {new_quantity} {self.unit}"
        )
        db.session.add(adjustment)
        db.session.commit()
    
    def __repr__(self):
        return f'<Ingredient {self.name}: {self.stock_quantity} {self.unit}>'


class RecipeBOM(db.Model):
    """
    Bill of Materials (BOM) - Recipe ingredients
    Links menu items to required ingredients and quantities
    """
    __tablename__ = 'recipe_bom'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity_used = db.Column(db.Numeric(10, 3), nullable=False)  # Quantity per serving
    notes = db.Column(db.Text)  # Additional notes for preparation
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    
    # Relationships
    menu = db.relationship('Menu', backref='recipe_items', lazy=True)
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('menu_id', 'ingredient_id', name='unique_menu_ingredient'),)
    
    def can_fulfill_quantity(self, serving_quantity=1):
        """Check if there's enough ingredient stock for the required quantity"""
        required_quantity = float(self.quantity_used) * serving_quantity
        available_quantity = float(self.ingredient.stock_quantity)
        return available_quantity >= required_quantity
    
    def deduct_for_order(self, serving_quantity=1, user_id=None):
        """Deduct ingredient stock for order fulfillment"""
        required_quantity = float(self.quantity_used) * serving_quantity
        notes = f"Used for menu: {self.menu.name} (x{serving_quantity})"
        return self.ingredient.deduct_stock(required_quantity, user_id, notes)
    
    def __repr__(self):
        return f'<RecipeBOM {self.menu.name}: {self.quantity_used} {self.ingredient.unit} of {self.ingredient.name}>'


class StockAdjustment(db.Model):
    """
    Stock adjustment history
    Tracks all stock movements for audit trail
    """
    __tablename__ = 'stock_adjustments'
    
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'in', 'out', 'correction'
    quantity = db.Column(db.Numeric(10, 3), nullable=False)  # Positive for in, negative for out
    previous_quantity = db.Column(db.Numeric(10, 3))  # Stock before adjustment
    new_quantity = db.Column(db.Numeric(10, 3))  # Stock after adjustment
    adjusted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    # Relationships
    adjusted_by_user = db.relationship('User', backref='stock_adjustments', lazy=True)
    
    def __repr__(self):
        return f'<StockAdjustment {self.type}: {self.quantity} of {self.ingredient.name}>'


class Promotion(db.Model):
    """
    Promotion and discount management
    Supports various promotion types for marketing campaigns
    """
    __tablename__ = 'promotions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(20), nullable=False)  # 'percentage', 'fixed_amount', 'buy_x_get_y'
    
    # Discount details
    discount_percentage = db.Column(db.Numeric(5, 2))  # For percentage discounts (0-100)
    discount_amount = db.Column(db.Numeric(10, 2))  # For fixed amount discounts
    
    # Buy X Get Y promotion details
    buy_quantity = db.Column(db.Integer)  # Items to buy
    get_quantity = db.Column(db.Integer)  # Items to get free
    
    # Conditions
    minimum_order_amount = db.Column(db.Numeric(10, 2), default=0)  # Minimum order total
    applicable_menu_ids = db.Column(db.Text)  # JSON array of menu IDs (null = all menus)
    
    # Validity
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Usage tracking
    usage_limit = db.Column(db.Integer)  # Maximum uses (null = unlimited)
    current_usage = db.Column(db.Integer, default=0, nullable=False)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    
    # Relationships
    creator = db.relationship('User', backref='created_promotions', lazy=True)
    
    def is_valid_now(self):
        """Check if promotion is currently valid"""
        now = get_thai_now()
        return (self.is_active and 
                self.start_date <= now <= self.end_date and
                (self.usage_limit is None or self.current_usage < self.usage_limit))
    
    def can_apply_to_order(self, order_total, menu_ids=None):
        """Check if promotion can be applied to an order"""
        if not self.is_valid_now():
            return False
        
        # Check minimum order amount
        if float(order_total) < float(self.minimum_order_amount):
            return False
        
        # Check applicable menus if specified
        if self.applicable_menu_ids and menu_ids:
            import json
            try:
                applicable_ids = json.loads(self.applicable_menu_ids)
                if not any(mid in applicable_ids for mid in menu_ids):
                    return False
            except:
                pass
        
        return True
    
    def calculate_discount(self, order_total, item_quantities=None):
        """Calculate discount amount for an order"""
        if not self.can_apply_to_order(order_total):
            return 0
        
        if self.type == 'percentage':
            return float(order_total) * (float(self.discount_percentage) / 100)
        elif self.type == 'fixed_amount':
            return min(float(self.discount_amount), float(order_total))
        elif self.type == 'buy_x_get_y' and item_quantities:
            # Simplified buy X get Y calculation
            # This would need more complex logic for real implementation
            total_items = sum(item_quantities.values())
            free_items = (total_items // self.buy_quantity) * self.get_quantity
            # Return estimated value of free items (simplified)
            return free_items * 50  # Assume average item price of ฿50
        
        return 0
    
    def use_promotion(self):
        """Increment usage counter"""
        self.current_usage += 1
        db.session.commit()
    
    def __repr__(self):
        return f'<Promotion {self.name} ({self.type})>'


# =============================================================================
# PHASE 2 UTILITY FUNCTIONS
# =============================================================================

def create_admin_user():
    """Create default admin user for development"""
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")
        else:
            print("Admin user already exists")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {e}")
    return admin


def create_sample_ingredients():
    """Create sample ingredients for development"""
    sample_ingredients = [
        {
            'name': 'ข้าวสวย',
            'description': 'ข้าวหอมมะลิสำหรับทำข้าวผัด',
            'stock_quantity': 50.0,
            'unit': 'กิโลกรัม',
            'low_stock_threshold': 5.0,
            'cost_per_unit': 45.0,
            'supplier': 'ร้านข้าวป้าสม'
        },
        {
            'name': 'เนื้อหมู',
            'description': 'เนื้อหมูสามชั้นสำหรับทำข้าวผัด',
            'stock_quantity': 20.0,
            'unit': 'กิโลกรัม',
            'low_stock_threshold': 3.0,
            'cost_per_unit': 180.0,
            'supplier': 'ตลาดสดใกล้บ้าน'
        },
        {
            'name': 'ไข่ไก่',
            'description': 'ไข่ไก่สดสำหรับทำข้าวผัด',
            'stock_quantity': 100.0,
            'unit': 'ฟอง',
            'low_stock_threshold': 20.0,
            'cost_per_unit': 4.5,
            'supplier': 'ฟาร์มไข่ลุงสมชาย'
        },
        {
            'name': 'น้ำมันพืช',
            'description': 'น้ำมันพืชสำหรับทอดและผัด',
            'stock_quantity': 15.0,
            'unit': 'ลิตร',
            'low_stock_threshold': 2.0,
            'cost_per_unit': 55.0,
            'supplier': 'ร้านของชำป้าแดง'
        },
        {
            'name': 'ผักชี',
            'description': 'ผักชีสดสำหรับโรยหน้าอาหาร',
            'stock_quantity': 5.0,
            'unit': 'กิโลกรัม',
            'low_stock_threshold': 0.5,
            'cost_per_unit': 40.0,
            'supplier': 'ตลาดสดใกล้บ้าน'
        }
    ]
    
    for ingredient_data in sample_ingredients:
        existing = Ingredient.query.filter_by(name=ingredient_data['name']).first()
        if not existing:
            ingredient = Ingredient(**ingredient_data)
            db.session.add(ingredient)
    
    db.session.commit()
    print("Sample ingredients created!")


def create_sample_bom():
    """Create sample Bill of Materials (BOM) for existing menu items"""
    # Find existing menu items
    fried_rice = Menu.query.filter_by(name='ข้าวผัดหมู').first()
    if not fried_rice:
        print("Menu item 'ข้าวผัดหมู' not found. Please create sample menu data first.")
        return
    
    # Find ingredients
    rice = Ingredient.query.filter_by(name='ข้าวสวย').first()
    pork = Ingredient.query.filter_by(name='เนื้อหมู').first()
    egg = Ingredient.query.filter_by(name='ไข่ไก่').first()
    oil = Ingredient.query.filter_by(name='น้ำมันพืช').first()
    cilantro = Ingredient.query.filter_by(name='ผักชี').first()
    
    if not all([rice, pork, egg, oil, cilantro]):
        print("Some ingredients not found. Please create sample ingredients first.")
        return
    
    # Create BOM for ข้าวผัดหมู
    bom_items = [
        {'ingredient': rice, 'quantity': 0.15},  # 150g rice per serving
        {'ingredient': pork, 'quantity': 0.08},  # 80g pork per serving
        {'ingredient': egg, 'quantity': 1.0},    # 1 egg per serving
        {'ingredient': oil, 'quantity': 0.02},   # 20ml oil per serving
        {'ingredient': cilantro, 'quantity': 0.005}  # 5g cilantro per serving
    ]
    
    for bom_data in bom_items:
        existing = RecipeBOM.query.filter_by(
            menu_id=fried_rice.id,
            ingredient_id=bom_data['ingredient'].id
        ).first()
        
        if not existing:
            bom = RecipeBOM(
                menu_id=fried_rice.id,
                ingredient_id=bom_data['ingredient'].id,
                quantity_used=bom_data['quantity'],
                notes=f"Required for {fried_rice.name}"
            )
            db.session.add(bom)
    
    db.session.commit()
    print("Sample BOM created for ข้าวผัดหมู!")


def create_sample_promotion():
    """Create sample promotion for testing"""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = create_admin_user()
    
    # Create a sample promotion
    from datetime import timedelta
    
    existing = Promotion.query.filter_by(name='ลดราคา 10% ทุกเมนู').first()
    if not existing:
        promotion = Promotion(
            name='ลดราคา 10% ทุกเมนู',
            description='โปรโมชันลดราคา 10% สำหรับทุกเมนูในร้าน',
            type='percentage',
            discount_percentage=10.0,
            minimum_order_amount=100.0,
            start_date=get_thai_now(),
            end_date=get_thai_now() + timedelta(days=30),
            is_active=True,
            usage_limit=1000,
            created_by=admin.id
        )
        db.session.add(promotion)
        db.session.commit()
        print("Sample promotion created!")


def create_sample_data():
    """Create sample data for testing and development"""
    
    # Sample delivery zones
    zone_names = ['โต๊ะ 1', 'โต๊ะ 2', 'โต๊ะ 3', 'โซน A', 'โซน B']
    zone_descriptions = [
        'โต๊ะที่ 1 ใกล้ทางเข้า',
        'โต๊ะที่ 2 กลางลาน',
        'โต๊ะที่ 3 มุมลาน',
        'โซนกางเต็นท์ A',
        'โซนกางเต็นท์ B'
    ]
    
    for i, (name, desc) in enumerate(zip(zone_names, zone_descriptions)):
        existing_zone = DeliveryZone.query.filter_by(name=name).first()
        if not existing_zone:
            zone = DeliveryZone(name=name, description=desc)
            db.session.add(zone)
    
    # Sample staff users
    users_to_create = [
        ('kitchen', 'kitchen123', 'kitchen_staff'),
        ('delivery', 'delivery123', 'delivery_staff')
    ]
    
    for username, password, role in users_to_create:
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
    
    # Sample menu items
    menus = [
        {
            'name': 'ชุดหมูสามใจ',
            'description': 'หมูสามชั้น, หมูคอ, หมูสันคอ พร้อมน้ำจิ้มซีฟู้ด',
            'price': 250.00,
            'category': 'อาหารจานเดียว'
        },
        {
            'name': 'เอ็นข้อไก่ทอด',
            'description': 'เอ็นข้อไก่ทอดกรอบ พร้อมน้ำจิ้มแจ่ว',
            'price': 120.00,
            'category': 'กับแกล้ม'
        },
        {
            'name': 'ข้าวผัดหมู',
            'description': 'ข้าวผัดหมูสับ ใส่ไข่ดาว',
            'price': 80.00,
            'category': 'อาหารจานเดียว'
        },
        {
            'name': 'น้ำเปล่า',
            'description': 'น้ำดื่มบรรจุขวด',
            'price': 15.00,
            'category': 'เครื่องดื่ม'
        },
        {
            'name': 'เบียร์ช้าง',
            'description': 'เบียร์ช้าง ขวดใหญ่',
            'price': 75.00,
            'category': 'เครื่องดื่ม'
        },
    ]
    
    for menu_data in menus:
        existing_menu = Menu.query.filter_by(name=menu_data['name']).first()
        if not existing_menu:
            menu = Menu(**menu_data)
            db.session.add(menu)
            db.session.flush()  # Get the ID
            
            # Add options for some menus
            if menu.name == 'ชุดหมูสามใจ':
                # เพิ่มท็อปปิ้ง group
                topping_group = MenuOptionGroup(
                    menu_id=menu.id,
                    name='เพิ่มท็อปปิ้ง',
                    is_required=False,
                    max_selections=3
                )
                db.session.add(topping_group)
                db.session.flush()
                
                toppings = [
                    ('เพิ่มสามชั้น', 30.00),
                    ('เพิ่มคอ', 25.00),
                    ('เพิ่มสันคอ', 35.00),
                ]
                
                for name, price in toppings:
                    option = MenuOptionItem(
                        group_id=topping_group.id,
                        name=name,
                        additional_price=price
                    )
                    db.session.add(option)
            
            elif menu.name == 'ข้าวผัดหมู':
                # เพิ่มท็อปปิ้ง group
                extra_group = MenuOptionGroup(
                    menu_id=menu.id,
                    name='เพิ่มเติม',
                    is_required=False,
                    max_selections=2
                )
                db.session.add(extra_group)
                db.session.flush()
                
                extras = [
                    ('ไข่ดาว', 10.00),
                    ('ชีส', 15.00),
                ]
                
                for name, price in extras:
                    option = MenuOptionItem(
                        group_id=extra_group.id,
                        name=name,
                        additional_price=price
                    )
                    db.session.add(option)
    
    # Commit all sample data
    try:
        db.session.commit()
        print("Sample data created successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample data: {e}")


def setup_phase2_data():
    """Setup all Phase 2 sample data"""
    print("Setting up Phase 2 sample data...")
    try:
        create_admin_user()
        create_sample_ingredients()
        create_sample_bom()
        create_sample_promotion()
        print("Phase 2 sample data setup complete!")
    except Exception as e:
        print(f"Error setting up Phase 2 data: {e}")
        db.session.rollback()


# =============================================================================
# PHASE 3 MODELS - Customer Experience Boost & Analytics
# =============================================================================

class DailyReport(db.Model):
    """
    Daily business reports for analytics
    Pre-computed daily statistics for performance
    """
    __tablename__ = 'daily_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    report_date = db.Column(db.Date, nullable=False, unique=True, index=True)
    
    # Order Statistics
    total_orders = db.Column(db.Integer, default=0)
    completed_orders = db.Column(db.Integer, default=0)
    cancelled_orders = db.Column(db.Integer, default=0)
    
    # Revenue Statistics
    gross_revenue = db.Column(db.Numeric(12, 2), default=0)
    net_revenue = db.Column(db.Numeric(12, 2), default=0)
    average_order_value = db.Column(db.Numeric(10, 2), default=0)
    
    # Customer Statistics
    total_customers = db.Column(db.Integer, default=0)
    returning_customers = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Numeric(3, 2), default=0)
    
    # Operational Hours
    peak_hour_start = db.Column(db.Time)
    peak_hour_end = db.Column(db.Time)
    peak_hour_orders = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    
    def __repr__(self):
        return f'<DailyReport {self.report_date} - {self.total_orders} orders>'

class HourlyStats(db.Model):
    """
    Hourly statistics for detailed analytics
    Track business patterns throughout the day
    """
    __tablename__ = 'hourly_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    hour = db.Column(db.Integer, nullable=False)  # 0-23
    
    order_count = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Numeric(10, 2), default=0)
    average_prep_time = db.Column(db.Integer, default=0)  # minutes
    
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('date', 'hour', name='unique_hour_stats'),)
    
    def __repr__(self):
        return f'<HourlyStats {self.date} {self.hour}:00 - {self.order_count} orders>'

class MenuPopularity(db.Model):
    """
    Menu item popularity tracking
    Track which items sell best over time
    """
    __tablename__ = 'menu_popularity'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    
    order_count = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Numeric(10, 2), default=0)
    average_rating = db.Column(db.Numeric(3, 2), default=0)
    total_ratings = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    
    # Relationships
    menu = db.relationship('Menu', backref='popularity_stats')
    
    __table_args__ = (db.UniqueConstraint('menu_id', 'date', name='unique_menu_date'),)
    
    def __repr__(self):
        return f'<MenuPopularity {self.menu.name} {self.date} - {self.order_count} orders>'

class CustomerSession(db.Model):
    """
    Track customer sessions and behavior
    For analytics and order flood prevention
    """
    __tablename__ = 'customer_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.Text)
    
    # Rate limiting
    order_count = db.Column(db.Integer, default=0)
    last_order_at = db.Column(db.DateTime)
    is_blocked = db.Column(db.Boolean, default=False)
    block_reason = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    last_activity = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    
    def can_place_order(self):
        """Check if session can place new order (rate limiting)"""
        if self.is_blocked:
            return False, self.block_reason
            
        # Check order frequency (max 3 orders per 10 minutes)
        if self.last_order_at:
            time_diff = get_thai_now() - self.last_order_at
            if time_diff.total_seconds() < 600 and self.order_count >= 3:  # 10 minutes
                return False, "คุณสั่งออเดอร์บ่อยเกินไป กรุณารอสักครู่"
        
        return True, None
    
    def record_order(self):
        """Record new order for rate limiting"""
        now = get_thai_now()
        
        # Reset counter if last order was more than 10 minutes ago
        if self.last_order_at and (now - self.last_order_at).total_seconds() > 600:
            self.order_count = 0
            
        self.order_count += 1
        self.last_order_at = now
        self.last_activity = now
    
    def __repr__(self):
        return f'<CustomerSession {self.session_id[:8]}... - {self.order_count} orders>'

# =============================================================================
# ANALYTICS UTILITY FUNCTIONS
# =============================================================================

def update_daily_report(target_date=None):
    """
    Update daily report for specified date
    Called by background tasks or manually
    """
    if target_date is None:
        target_date = get_thai_now().date()
    
    # Get existing report or create new one
    report = DailyReport.query.filter_by(report_date=target_date).first()
    if not report:
        report = DailyReport(report_date=target_date)
        db.session.add(report)
    
    # Calculate order statistics
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    
    daily_orders = Order.query.filter(
        Order.created_at >= day_start,
        Order.created_at < day_end
    ).all()
    
    report.total_orders = len(daily_orders)
    report.completed_orders = len([o for o in daily_orders if o.status in ['delivered', 'completed']])
    report.cancelled_orders = len([o for o in daily_orders if o.status == 'cancelled'])
    
    # Calculate revenue
    completed_orders = [o for o in daily_orders if o.status in ['delivered', 'completed']]
    report.gross_revenue = sum(float(o.total_price) for o in completed_orders)
    report.net_revenue = report.gross_revenue  # Can subtract costs later
    report.average_order_value = (
        report.gross_revenue / len(completed_orders) if completed_orders else 0
    )
    
    # Calculate customer statistics
    customer_names = set(o.customer_name for o in daily_orders if o.customer_name)
    report.total_customers = len(customer_names)
    
    # Calculate average rating
    feedbacks = Feedback.query.join(Order).filter(
        Order.created_at >= day_start,
        Order.created_at < day_end
    ).all()
    
    if feedbacks:
        report.average_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
    
    # Find peak hour
    hourly_counts = {}
    for order in daily_orders:
        hour = order.created_at.hour
        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
    
    if hourly_counts:
        peak_hour = max(hourly_counts.items(), key=lambda x: x[1])
        report.peak_hour_start = datetime.min.time().replace(hour=peak_hour[0])
        report.peak_hour_end = datetime.min.time().replace(hour=(peak_hour[0] + 1) % 24)
        report.peak_hour_orders = peak_hour[1]
    
    db.session.commit()
    return report

def update_hourly_stats(target_date=None, target_hour=None):
    """
    Update hourly statistics
    """
    now = get_thai_now()
    if target_date is None:
        target_date = now.date()
    if target_hour is None:
        target_hour = now.hour
    
    # Get existing stats or create new
    stats = HourlyStats.query.filter_by(date=target_date, hour=target_hour).first()
    if not stats:
        stats = HourlyStats(date=target_date, hour=target_hour)
        db.session.add(stats)
    
    # Calculate hour range
    hour_start = datetime.combine(target_date, datetime.min.time().replace(hour=target_hour))
    hour_end = hour_start + timedelta(hours=1)
    
    # Get orders for this hour
    hour_orders = Order.query.filter(
        Order.created_at >= hour_start,
        Order.created_at < hour_end
    ).all()
    
    stats.order_count = len(hour_orders)
    completed_orders = [o for o in hour_orders if o.status in ['delivered', 'completed']]
    stats.revenue = sum(float(o.total_price) for o in completed_orders)
    
    db.session.commit()
    return stats

def update_menu_popularity(target_date=None):
    """
    Update menu popularity statistics
    """
    if target_date is None:
        target_date = get_thai_now().date()
    
    # Get all menu items
    menus = Menu.query.filter_by(is_active=True).all()
    
    for menu in menus:
        # Get existing popularity or create new
        popularity = MenuPopularity.query.filter_by(
            menu_id=menu.id, 
            date=target_date
        ).first()
        
        if not popularity:
            popularity = MenuPopularity(menu_id=menu.id, date=target_date)
            db.session.add(popularity)
        
        # Calculate statistics for this menu on this date
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        
        # Get order items for this menu
        order_items = OrderItem.query.join(Order).filter(
            OrderItem.menu_id == menu.id,
            Order.created_at >= day_start,
            Order.created_at < day_end,
            Order.status.in_(['delivered', 'completed'])
        ).all()
        
        popularity.order_count = len(order_items)
        popularity.revenue = sum(float(item.price_per_item) * item.quantity for item in order_items)
        
        # Calculate average rating from feedback
        feedbacks = db.session.query(Feedback).join(Order).join(OrderItem).filter(
            OrderItem.menu_id == menu.id,
            Order.created_at >= day_start,
            Order.created_at < day_end
        ).all()
        
        if feedbacks:
            popularity.average_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
            popularity.total_ratings = len(feedbacks)
    
    db.session.commit()

class PaymentTransaction(db.Model):
    """
    Payment transaction model for tracking payments
    Supports multiple payment methods with verification
    """
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cod, bank_transfer, promptpay, etc.
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    processing_fee = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed, cancelled, refunded
    payment_data = db.Column(db.Text)  # JSON string for method-specific data
    verification_data = db.Column(db.Text)  # Slip images, transaction refs, etc.
    created_at = db.Column(db.DateTime, default=get_thai_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_thai_now, onupdate=get_thai_now)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    order = db.relationship('Order', backref=db.backref('payment_transactions', lazy=True))
    
    def __repr__(self):
        return f'<PaymentTransaction {self.transaction_id}: {self.amount} via {self.payment_method}>'
