"""
Security Enhancement Module
Provides security middleware and utilities for production
"""

from flask import request, abort, g
from functools import wraps
import hashlib
import hmac
import time
import re
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self, app=None):
        self.app = app
        self.failed_login_attempts = {}
        self.blocked_ips = set()
        
    def init_app(self, app):
        """Initialize security with Flask app"""
        self.app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
    def before_request(self):
        """Security checks before each request"""
        # Check if IP is blocked
        client_ip = self.get_client_ip()
        if client_ip in self.blocked_ips:
            abort(403)
            
        # Rate limiting check
        if self.is_rate_limited(client_ip):
            abort(429)
            
        # Log suspicious activity
        self.log_suspicious_activity()
        
    def after_request(self, response):
        """Add security headers to response"""
        if self.app.config.get('SECURITY_HEADERS'):
            for header, value in self.app.config['SECURITY_HEADERS'].items():
                response.headers[header] = value
        return response
        
    def get_client_ip(self):
        """Get real client IP address"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr
        
    def is_rate_limited(self, ip):
        """Simple rate limiting implementation"""
        current_time = time.time()
        key = f"rate_limit_{ip}"
        
        if not hasattr(g, 'rate_limit_cache'):
            g.rate_limit_cache = {}
            
        if key not in g.rate_limit_cache:
            g.rate_limit_cache[key] = []
            
        # Clean old requests (older than 1 hour)
        g.rate_limit_cache[key] = [
            req_time for req_time in g.rate_limit_cache[key] 
            if current_time - req_time < 3600
        ]
        
        # Add current request
        g.rate_limit_cache[key].append(current_time)
        
        # Check if rate limit exceeded
        return len(g.rate_limit_cache[key]) > 100
        
    def log_suspicious_activity(self):
        """Log potentially suspicious activity"""
        user_agent = request.headers.get('User-Agent', '')
        
        # Check for common attack patterns
        suspicious_patterns = [
            r'(?i)(union|select|insert|update|delete|drop|create|alter)',
            r'(?i)(<script|javascript:|vbscript:)',
            r'(?i)(\.\.\/|\.\.\\)',
            r'(?i)(exec|eval|system|passthru)'
        ]
        
        url = request.url
        for pattern in suspicious_patterns:
            if re.search(pattern, url) or re.search(pattern, str(request.get_data())):
                logger.warning(f"Suspicious activity detected from {self.get_client_ip()}: {url}")
                break
                
    def record_failed_login(self, identifier):
        """Record failed login attempt"""
        current_time = time.time()
        if identifier not in self.failed_login_attempts:
            self.failed_login_attempts[identifier] = []
            
        self.failed_login_attempts[identifier].append(current_time)
        
        # Clean old attempts (older than 1 hour)
        self.failed_login_attempts[identifier] = [
            attempt_time for attempt_time in self.failed_login_attempts[identifier]
            if current_time - attempt_time < 3600
        ]
        
        # Block if too many failed attempts
        if len(self.failed_login_attempts[identifier]) >= 5:
            self.blocked_ips.add(self.get_client_ip())
            logger.warning(f"IP {self.get_client_ip()} blocked due to multiple failed login attempts")
            
    def is_login_blocked(self, identifier):
        """Check if login is temporarily blocked"""
        if identifier not in self.failed_login_attempts:
            return False
            
        current_time = time.time()
        recent_attempts = [
            attempt_time for attempt_time in self.failed_login_attempts[identifier]
            if current_time - attempt_time < 900  # 15 minutes
        ]
        
        return len(recent_attempts) >= 3

def secure_password(password):
    """Generate secure password hash"""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(password, password_hash):
    """Verify password against hash"""
    return check_password_hash(password_hash, password)

def admin_required(f):
    """Enhanced admin required decorator with security logging"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            logger.warning(f"Unauthenticated access attempt to admin route: {request.endpoint}")
            abort(401)
            
        if not getattr(current_user, 'is_admin', False):
            logger.warning(f"Non-admin user {current_user.username} attempted to access admin route: {request.endpoint}")
            abort(403)
            
        return f(*args, **kwargs)
    return decorated_function

def validate_file_upload(file):
    """Validate uploaded file for security"""
    if not file or not file.filename:
        return False, "ไม่พบไฟล์"
        
    # Check file extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_extension not in allowed_extensions:
        return False, "ประเภทไฟล์ไม่ได้รับอนุญาต"
        
    # Check file size (5MB max)
    if hasattr(file, 'content_length') and file.content_length > 5 * 1024 * 1024:
        return False, "ไฟล์ใหญ่เกินไป (สูงสุด 5MB)"
        
    # Read file header to verify it's actually an image
    file.seek(0)
    header = file.read(512)
    file.seek(0)
    
    # Check for image magic numbers
    image_signatures = [
        b'\xFF\xD8\xFF',  # JPEG
        b'\x89PNG\r\n\x1a\n',  # PNG
        b'GIF87a',  # GIF
        b'GIF89a',  # GIF
        b'RIFF',  # WebP (needs additional check)
    ]
    
    is_valid_image = any(header.startswith(sig) for sig in image_signatures)
    if not is_valid_image:
        return False, "ไฟล์ไม่ใช่รูปภาพที่ถูกต้อง"
        
    return True, "OK"

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    import uuid
    import os
    
    # Keep only the file extension
    ext = os.path.splitext(filename)[1].lower()
    
    # Generate safe filename
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    
    return safe_filename

# Global security manager instance
security_manager = SecurityManager()
