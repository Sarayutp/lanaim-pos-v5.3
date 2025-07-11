"""
LanAim POS System v2.4 - Phase 2
Main Application Factory and Configuration

This is the main Flask application factory that initializes all components
of the LanAim POS system including database, authentication, admin panel,
and real-time features.
"""

from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
import os

# Import configuration
from config import config

# Import models and database
from models import db, init_db, User

# Initialize extensions
login_manager = LoginManager()
socketio = SocketIO()

def create_app(config_name=None):
    """
    Application factory pattern for Flask app creation
    
    Args:
        config_name (str): Configuration environment ('development', 'production', etc.)
    
    Returns:
        Flask: Configured Flask application instance
    """
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    init_extensions(app)
    
    # Initialize database
    init_db(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

def init_extensions(app):
    """Initialize Flask extensions"""
    
    # Initialize database
    db.init_app(app)
    
    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = 'staff.login'
    login_manager.login_message = 'กรุณาเข้าสู่ระบบเพื่อเข้าถึงหน้านี้'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user for Flask-Login"""
        return db.session.get(User, int(user_id))
    
    # Initialize SocketIO for real-time features (using threading for Python 3.13 compatibility)
    socketio.init_app(
        app, 
        async_mode='threading',
        cors_allowed_origins="*",  # Allow all origins in development
        logger=app.config.get('SOCKETIO_LOGGER', False),
        engineio_logger=app.config.get('SOCKETIO_ENGINEIO_LOGGER', False)
    )

def register_blueprints(app):
    """Register application blueprints"""
    
    # Import blueprints
    from routes.customer import customer_bp
    from routes.staff import staff_bp
    from routes.api import api_bp
    from routes.admin import admin_bp  # Phase 2 addition
    from routes.admin.api import admin_api_bp  # Phase 1 addition - Admin API
    
    # Phase 2 additions - Enhanced systems
    from cart_system import cart_bp
    from order_system import order_bp
    from kitchen_system import kitchen_bp
    from payment_system import payment_bp
    
    # Register blueprints with URL prefixes
    app.register_blueprint(customer_bp, url_prefix='/')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')  # Phase 2 addition
    app.register_blueprint(admin_api_bp)  # Admin API endpoints
    
    # Phase 2 enhanced systems
    app.register_blueprint(cart_bp)  # /api/cart/*
    app.register_blueprint(order_bp)  # /api/order/*
    app.register_blueprint(kitchen_bp)  # /kitchen/*
    app.register_blueprint(payment_bp)  # /api/payment/*

def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'ไม่พบหน้าที่ต้องการ'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'เกิดข้อผิดพลาดภายในระบบ'}, 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return {'error': 'ไม่มีสิทธิ์เข้าถึง'}, 403

# Create the main app instance
app = create_app()

if __name__ == '__main__':
    # Run the application with SocketIO support
    # Phase 3 runs on port 5002
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5002, 
        debug=True
    )
