"""
Admin Blueprint Package
Phase 3 - Admin & Analytics Enhancement

This package contains all admin-related routes for the LanAim POS system.
Includes menu management, ingredient/stock management, zone management,
promotion management, and comprehensive analytics.
"""

from flask import Blueprint

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Import all admin route modules
from . import auth
from . import dashboard
from . import menu_management
from . import ingredient_management
from . import zone_management
from . import promotion_management
from . import reports
from . import analytics  # Phase 3 addition
from . import api  # Phase 1 addition - API endpoints
