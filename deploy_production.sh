#!/bin/bash

# Production Deployment Script
# Automates the deployment process for LanAim POS System

set -e  # Exit on any error

echo "🚀 Starting LanAim POS Production Deployment..."

# Configuration
APP_NAME="lanaim-pos"
APP_DIR="/opt/lanaim-pos"
BACKUP_DIR="/opt/lanaim-pos/backups"
VENV_DIR="/opt/lanaim-pos/venv"
SERVICE_NAME="lanaim-pos"
USER="lanaim"
GROUP="lanaim"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
    print_success "Running as root"
}

# Update system packages
update_system() {
    print_status "Updating system packages..."
    
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get upgrade -y
        apt-get install -y python3 python3-pip python3-venv nginx redis-server supervisor
    elif command -v yum &> /dev/null; then
        yum update -y
        yum install -y python3 python3-pip nginx redis supervisor
    else
        print_error "Unsupported package manager"
        exit 1
    fi
    
    print_success "System packages updated"
}

# Create application user
create_user() {
    print_status "Creating application user..."
    
    if ! id "$USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$APP_DIR" "$USER"
        print_success "Created user: $USER"
    else
        print_warning "User $USER already exists"
    fi
}

# Create directory structure
create_directories() {
    print_status "Creating directory structure..."
    
    mkdir -p "$APP_DIR"
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/backups"
    mkdir -p "$APP_DIR/uploads"
    mkdir -p "$APP_DIR/static"
    mkdir -p "$APP_DIR/templates"
    mkdir -p "/etc/lanaim-pos"
    
    print_success "Directory structure created"
}

# Setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    
    # Install requirements
    if [[ -f "requirements_production.txt" ]]; then
        pip install -r requirements_production.txt
        print_success "Production requirements installed"
    else
        print_warning "requirements_production.txt not found, installing basic requirements"
        pip install Flask gunicorn redis psutil schedule flask-socketio
    fi
}

# Copy application files
deploy_application() {
    print_status "Deploying application files..."
    
    # Copy Python files
    cp *.py "$APP_DIR/"
    
    # Copy templates and static files
    if [[ -d "templates" ]]; then
        cp -r templates "$APP_DIR/"
    fi
    
    if [[ -d "static" ]]; then
        cp -r static "$APP_DIR/"
    fi
    
    # Create instance directory if it doesn't exist
    mkdir -p "$APP_DIR/instance"
    
    print_success "Application files deployed"
}

# Setup production configuration
setup_configuration() {
    print_status "Setting up production configuration..."
    
    # Create environment file
    cat > "/etc/lanaim-pos/production.env" << EOF
# LanAim POS Production Configuration
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=sqlite:///$APP_DIR/instance/lanaim_production.db
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
APP_VERSION=5.3
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
MONITORING_ENABLED=true
SECURITY_ENABLED=true
EOF

    print_success "Production configuration created"
}

# Setup Nginx configuration
setup_nginx() {
    print_status "Setting up Nginx configuration..."
    
    cat > "/etc/nginx/sites-available/lanaim-pos" << EOF
server {
    listen 80;
    server_name _;  # Replace with your domain
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # Static files
    location /static {
        alias $APP_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/lanaim-pos /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    nginx -t
    
    print_success "Nginx configuration completed"
}

# Setup Supervisor configuration
setup_supervisor() {
    print_status "Setting up Supervisor configuration..."
    
    cat > "/etc/supervisor/conf.d/lanaim-pos.conf" << EOF
[program:lanaim-pos]
command=$VENV_DIR/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --worker-class eventlet --worker-connections 1000 --timeout 30 --keep-alive 2 app_production:app
directory=$APP_DIR
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$APP_DIR/logs/gunicorn.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="$VENV_DIR/bin",FLASK_ENV="production"
EOF

    print_success "Supervisor configuration completed"
}

# Setup Redis configuration
setup_redis() {
    print_status "Setting up Redis configuration..."
    
    # Basic Redis security
    sed -i 's/^# bind 127.0.0.1/bind 127.0.0.1/' /etc/redis/redis.conf
    sed -i 's/^# requirepass/requirepass/' /etc/redis/redis.conf
    
    systemctl enable redis-server
    systemctl restart redis-server
    
    print_success "Redis configuration completed"
}

# Setup database
setup_database() {
    print_status "Setting up database..."
    
    cd "$APP_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Load environment variables
    export $(grep -v '^#' /etc/lanaim-pos/production.env | xargs)
    
    # Initialize database
    python3 -c "
from app_production import create_production_app
app = create_production_app()
with app.app_context():
    from models import db
    db.create_all()
    print('Database initialized')
"
    
    print_success "Database setup completed"
}

# Set permissions
set_permissions() {
    print_status "Setting file permissions..."
    
    chown -R "$USER:$GROUP" "$APP_DIR"
    chmod -R 755 "$APP_DIR"
    chmod -R 644 "$APP_DIR"/*.py
    chmod 700 "$APP_DIR/instance"
    chmod 700 "$APP_DIR/backups"
    chmod 755 "$APP_DIR/logs"
    
    # Make start script executable
    if [[ -f "$APP_DIR/start_production.sh" ]]; then
        chmod +x "$APP_DIR/start_production.sh"
    fi
    
    print_success "File permissions set"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    # Start Redis
    systemctl start redis-server
    systemctl enable redis-server
    
    # Start Supervisor
    systemctl start supervisor
    systemctl enable supervisor
    supervisorctl reread
    supervisorctl update
    supervisorctl start lanaim-pos
    
    # Start Nginx
    systemctl start nginx
    systemctl enable nginx
    
    print_success "All services started"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check if application is responding
    sleep 5
    
    if curl -f http://localhost/health > /dev/null 2>&1; then
        print_success "Application is responding to health checks"
    else
        print_error "Application health check failed"
        return 1
    fi
    
    # Check service status
    if systemctl is-active --quiet nginx; then
        print_success "Nginx is running"
    else
        print_error "Nginx is not running"
    fi
    
    if systemctl is-active --quiet redis-server; then
        print_success "Redis is running"
    else
        print_error "Redis is not running"
    fi
    
    if supervisorctl status lanaim-pos | grep -q RUNNING; then
        print_success "LanAim POS application is running"
    else
        print_error "LanAim POS application is not running"
    fi
}

# Create startup script
create_startup_script() {
    print_status "Creating startup script..."
    
    cat > "$APP_DIR/start_production.sh" << 'EOF'
#!/bin/bash

# LanAim POS Production Startup Script

APP_DIR="/opt/lanaim-pos"
VENV_DIR="/opt/lanaim-pos/venv"

cd "$APP_DIR"
source "$VENV_DIR/bin/activate"

# Load environment variables
export $(grep -v '^#' /etc/lanaim-pos/production.env | xargs)

# Start the application
exec gunicorn --bind 127.0.0.1:8000 \
    --workers 4 \
    --worker-class eventlet \
    --worker-connections 1000 \
    --timeout 30 \
    --keep-alive 2 \
    --access-logfile "$APP_DIR/logs/access.log" \
    --error-logfile "$APP_DIR/logs/error.log" \
    --log-level info \
    app_production:app
EOF

    chmod +x "$APP_DIR/start_production.sh"
    print_success "Startup script created"
}

# Main deployment function
main() {
    print_status "Starting LanAim POS Production Deployment"
    
    check_root
    update_system
    create_user
    create_directories
    setup_python_env
    deploy_application
    setup_configuration
    setup_nginx
    setup_supervisor
    setup_redis
    setup_database
    create_startup_script
    set_permissions
    start_services
    verify_deployment
    
    print_success "🎉 LanAim POS Production Deployment Completed!"
    echo ""
    echo "Application is now running at: http://your-server-ip"
    echo "Admin panel: http://your-server-ip/admin"
    echo "Health check: http://your-server-ip/health"
    echo ""
    echo "Log files:"
    echo "  - Application: $APP_DIR/logs/gunicorn.log"
    echo "  - Nginx: /var/log/nginx/access.log"
    echo "  - Redis: /var/log/redis/redis-server.log"
    echo ""
    echo "Configuration files:"
    echo "  - Environment: /etc/lanaim-pos/production.env"
    echo "  - Nginx: /etc/nginx/sites-available/lanaim-pos"
    echo "  - Supervisor: /etc/supervisor/conf.d/lanaim-pos.conf"
    echo ""
    echo "Useful commands:"
    echo "  - Restart app: supervisorctl restart lanaim-pos"
    echo "  - View logs: tail -f $APP_DIR/logs/gunicorn.log"
    echo "  - Check status: supervisorctl status"
}

# Run main function
main "$@"
