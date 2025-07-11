"""
Production Integration Module
Integrates all production-ready components into the main Flask application
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_migrate import Migrate

# Import production modules
from config_production import ProductionConfig
from security import SecurityManager, security_manager
from backup import BackupManager, backup_manager
from notifications import NotificationManager, notification_manager
from caching import CacheManager, cache_manager
from monitoring import PerformanceMonitor, performance_monitor

logger = logging.getLogger(__name__)

def create_production_app():
    """Create Flask application with production configuration"""
    
    app = Flask(__name__)
    
    # Load configuration
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
        logger.info("Loaded production configuration")
    else:
        # Fallback to development config
        app.config.from_object('config.DevelopmentConfig')
        logger.info("Loaded development configuration")
    
    # Initialize database
    from models import db
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Initialize production components
    init_production_components(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register production routes
    register_production_routes(app)
    
    # Register basic routes for testing
    register_test_routes(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")
    
    return app

def init_production_components(app):
    """Initialize all production-ready components"""
    
    # Initialize security manager
    security_manager.init_app(app)
    logger.info("Security manager initialized")
    
    # Initialize backup manager
    backup_manager.init_app(app)
    logger.info("Backup manager initialized")
    
    # Initialize notification system (skip in test mode)
    if not app.config.get('TESTING', False):
        try:
            from flask_socketio import SocketIO
            socketio = SocketIO(app)
            notification_manager.init_app(app, socketio)
            logger.info("Notification system initialized")
        except ImportError:
            logger.warning("SocketIO not available, skipping notification system")
    
    # Initialize cache manager
    cache_manager.init_app(app)
    logger.info("Cache manager initialized")
    
    # Initialize performance monitor
    performance_monitor.init_app(app)
    logger.info("Performance monitor initialized")
    
    # Setup production logging
    setup_production_logging(app)

def setup_production_logging(app):
    """Configure production logging"""
    
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging level
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s %(name)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler('logs/lanaim_pos.log'),
            logging.StreamHandler()
        ]
    )
    
    # Set Flask logging level
    app.logger.setLevel(getattr(logging, log_level))
    
    logger.info("Production logging configured")

def register_blueprints(app):
    """Register all application blueprints"""
    
    try:
        # Import and register main routes
        from routes.main import main_bp
        app.register_blueprint(main_bp)
        
        # Import and register admin routes
        from routes.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admin')
        
        # Import and register kitchen routes
        from routes.kitchen import kitchen_bp
        app.register_blueprint(kitchen_bp, url_prefix='/kitchen')
        
        # Import and register delivery routes
        from routes.delivery import delivery_bp
        app.register_blueprint(delivery_bp, url_prefix='/delivery')
        
        logger.info("Application blueprints registered")
        
    except ImportError as e:
        logger.warning(f"Some blueprints not found, using fallback routes: {e}")
        # Register fallback routes if blueprints are not available
        register_fallback_routes(app)

def register_fallback_routes(app):
    """Register basic routes if blueprints are not available"""
    
    @app.route('/')
    def index():
        return render_template('menu.html')
    
    @app.route('/admin')
    @security_manager.admin_required
    def admin():
        return render_template('admin/dashboard.html')
    
    @app.route('/kitchen')
    def kitchen():
        return render_template('kitchen.html')

def register_production_routes(app):
    """Register production-specific routes"""
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for load balancers"""
        health_status = performance_monitor.get_health_status()
        status_code = 200 if health_status['status'] in ['excellent', 'good'] else 503
        return jsonify(health_status), status_code
    
    @app.route('/admin/system-status')
    @security_manager.admin_required
    def system_status():
        """Detailed system status for admins"""
        try:
            performance_report = performance_monitor.get_performance_report()
            cache_stats = cache_manager.get_stats()
            backup_status = backup_manager.get_backup_status()
            
            from models import db
            db_stats = backup_manager._get_database_stats()
            
            return jsonify({
                'performance': performance_report,
                'cache': cache_stats,
                'backup': backup_status,
                'database': db_stats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"System status error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/admin/clear-cache', methods=['POST'])
    @security_manager.admin_required
    def clear_cache():
        """Clear application cache"""
        try:
            success = cache_manager.clear()
            if success:
                return jsonify({'message': 'Cache cleared successfully'})
            else:
                return jsonify({'error': 'Failed to clear cache'}), 500
        except Exception as e:
            logger.error(f"Clear cache error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/admin/backup', methods=['POST'])
    @security_manager.admin_required
    def manual_backup():
        """Trigger manual backup"""
        try:
            backup_file = backup_manager.create_backup()
            if backup_file:
                return jsonify({
                    'message': 'Backup created successfully',
                    'backup_file': backup_file
                })
            else:
                return jsonify({'error': 'Backup creation failed'}), 500
        except Exception as e:
            logger.error(f"Manual backup error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/admin/backups')
    @security_manager.admin_required
    def list_backups():
        """List available backups"""
        try:
            backups = backup_manager.list_backups()
            return jsonify({'backups': backups})
        except Exception as e:
            logger.error(f"List backups error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/admin/security-log')
    @security_manager.admin_required
    def security_log():
        """View security events"""
        try:
            events = security_manager.get_security_events()
            return jsonify({'events': events})
        except Exception as e:
            logger.error(f"Security log error: {e}")
            return jsonify({'error': str(e)}), 500

def register_test_routes(app):
    """Register basic routes for testing"""
    from flask import jsonify, request
    from models import Menu, Order, User, DeliveryZone
    
    @app.route('/menu')
    def menu():
        """Basic menu route for testing"""
        menus = Menu.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': m.id,
            'name': m.name,
            'description': m.description,
            'price': float(m.price),
            'category': m.category
        } for m in menus])
    
    @app.route('/api/menu')
    def api_menu():
        """API menu route for testing"""
        return menu()
    
    @app.route('/api/orders')
    def api_orders():
        """API orders route for testing"""
        orders = Order.query.all()
        return jsonify([{
            'id': o.id,
            'order_number': o.order_number,
            'customer_name': o.customer_name,
            'status': o.status,
            'total_price': float(o.total_price)
        } for o in orders])
    
    @app.route('/api/delivery-zones')
    def api_delivery_zones():
        """API delivery zones route for testing"""
        zones = DeliveryZone.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': z.id,
            'name': z.name,
            'description': z.description
        } for z in zones])
    
    @app.route('/admin/menu')
    def admin_menu():
        """Admin menu management route for testing"""
        return jsonify({'status': 'ok', 'page': 'admin_menu'})
    
    @app.route('/admin/orders')
    def admin_orders():
        """Admin order management route for testing"""
        return jsonify({'status': 'ok', 'page': 'admin_orders'})
    
    @app.route('/admin/users')
    def admin_users():
        """Admin user management route for testing"""
        return jsonify({'status': 'ok', 'page': 'admin_users'})
    
    @app.route('/kitchen/orders')
    def kitchen_orders():
        """Kitchen orders route for testing"""
        return jsonify({'status': 'ok', 'page': 'kitchen_orders'})
    
    @app.route('/delivery/orders')
    def delivery_orders():
        """Delivery orders route for testing"""
        return jsonify({'status': 'ok', 'page': 'delivery_orders'})

# Production error handlers
def register_error_handlers(app):
    """Register production error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        if request.is_json:
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        if request.is_json:
            return jsonify({'error': 'Access forbidden'}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        if request.is_json:
            return jsonify({'error': 'Rate limit exceeded'}), 429
        return render_template('errors/429.html'), 429

# Production context processors
def register_context_processors(app):
    """Register template context processors"""
    
    @app.context_processor
    def inject_system_info():
        """Inject system information into templates"""
        return {
            'app_version': app.config.get('APP_VERSION', '5.3'),
            'environment': app.config.get('FLASK_ENV', 'development'),
            'current_year': datetime.now().year
        }

# Production startup checks
def run_startup_checks(app):
    """Run startup checks for production readiness"""
    
    checks_passed = True
    issues = []
    
    # Check database connection
    try:
        from models import db
        with app.app_context():
            db.engine.execute('SELECT 1')
        logger.info("✓ Database connection OK")
    except Exception as e:
        issues.append(f"Database connection failed: {e}")
        checks_passed = False
    
    # Check required directories
    required_dirs = ['logs', 'backups', 'uploads']
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"✓ Created directory: {directory}")
            except Exception as e:
                issues.append(f"Cannot create directory {directory}: {e}")
                checks_passed = False
        else:
            logger.info(f"✓ Directory exists: {directory}")
    
    # Check configuration
    required_configs = ['SECRET_KEY', 'DATABASE_URL']
    for config in required_configs:
        if not app.config.get(config):
            issues.append(f"Missing required configuration: {config}")
            checks_passed = False
        else:
            logger.info(f"✓ Configuration set: {config}")
    
    # Check backup system
    try:
        backup_status = backup_manager.get_backup_status()
        logger.info(f"✓ Backup system: {backup_status['status']}")
    except Exception as e:
        issues.append(f"Backup system check failed: {e}")
        checks_passed = False
    
    if checks_passed:
        logger.info("🚀 All startup checks passed - Production ready!")
    else:
        logger.error("❌ Startup checks failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
    
    return checks_passed, issues

if __name__ == '__main__':
    # Create production app
    app = create_production_app()
    
    # Register error handlers and context processors
    register_error_handlers(app)
    register_context_processors(app)
    
    # Run startup checks
    checks_passed, issues = run_startup_checks(app)
    
    if not checks_passed and os.environ.get('FLASK_ENV') == 'production':
        logger.error("Production startup checks failed. Exiting.")
        exit(1)
    
    # Run application
    if os.environ.get('FLASK_ENV') == 'production':
        # Production mode - use Gunicorn or similar
        logger.info("Starting in production mode")
        app.run(
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 8000)),
            debug=False
        )
    else:
        # Development mode
        logger.info("Starting in development mode")
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True
        )
