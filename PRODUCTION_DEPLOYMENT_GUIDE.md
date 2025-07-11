# LanAim POS v5.3 Production Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying LanAim POS v5.3 to a production environment with full security, monitoring, and backup capabilities.

## System Requirements

### Minimum Hardware
- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 4GB (8GB+ recommended)
- **Storage**: 20GB+ SSD
- **Network**: Stable internet connection

### Supported Operating Systems
- Ubuntu 20.04 LTS or newer
- CentOS 8 or newer
- Debian 11 or newer
- RHEL 8 or newer

### Required Software
- Python 3.8+
- Nginx
- Redis Server
- Supervisor
- Git (for deployment)

## Pre-Deployment Checklist

### 1. Server Preparation
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx redis-server supervisor git curl
```

### 2. Security Setup
```bash
# Create non-root user (if not exists)
sudo adduser deploy
sudo usermod -aG sudo deploy

# Setup SSH key authentication (recommended)
# Disable password authentication in /etc/ssh/sshd_config
```

### 3. Firewall Configuration
```bash
# Allow SSH, HTTP, and HTTPS
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

1. **Download the deployment script**:
```bash
wget https://your-server/deploy_production.sh
chmod +x deploy_production.sh
```

2. **Run the deployment script**:
```bash
sudo ./deploy_production.sh
```

The script will automatically:
- Install dependencies
- Create application user
- Setup directory structure
- Configure services
- Deploy the application
- Start all services

### Method 2: Manual Deployment

#### Step 1: Create Application Structure
```bash
# Create application directory
sudo mkdir -p /opt/lanaim-pos
sudo mkdir -p /opt/lanaim-pos/{logs,backups,uploads,instance}

# Create application user
sudo useradd -r -s /bin/false -d /opt/lanaim-pos lanaim
```

#### Step 2: Setup Python Environment
```bash
# Create virtual environment
cd /opt/lanaim-pos
sudo python3 -m venv venv
sudo chown -R lanaim:lanaim venv

# Activate environment and install requirements
sudo -u lanaim venv/bin/pip install --upgrade pip
sudo -u lanaim venv/bin/pip install -r requirements_production.txt
```

#### Step 3: Deploy Application Files
```bash
# Copy application files
sudo cp *.py /opt/lanaim-pos/
sudo cp -r templates /opt/lanaim-pos/
sudo cp -r static /opt/lanaim-pos/

# Set ownership
sudo chown -R lanaim:lanaim /opt/lanaim-pos
```

#### Step 4: Configure Environment
```bash
# Create production environment file
sudo tee /etc/lanaim-pos/production.env << EOF
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=sqlite:///opt/lanaim-pos/instance/lanaim_production.db
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
APP_VERSION=5.3
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
MONITORING_ENABLED=true
SECURITY_ENABLED=true
EOF
```

#### Step 5: Configure Nginx
```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/lanaim-pos << EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Static files
    location /static {
        alias /opt/lanaim-pos/static;
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
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/lanaim-pos /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
```

#### Step 6: Configure Supervisor
```bash
# Create Supervisor configuration
sudo tee /etc/supervisor/conf.d/lanaim-pos.conf << EOF
[program:lanaim-pos]
command=/opt/lanaim-pos/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --worker-class eventlet app_production:app
directory=/opt/lanaim-pos
user=lanaim
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/lanaim-pos/logs/gunicorn.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="/opt/lanaim-pos/venv/bin"
EOF
```

#### Step 7: Initialize Database
```bash
# Initialize the database
cd /opt/lanaim-pos
sudo -u lanaim bash -c '
    source venv/bin/activate
    export $(grep -v "^#" /etc/lanaim-pos/production.env | xargs)
    python3 -c "
from app_production import create_production_app
app = create_production_app()
with app.app_context():
    from models import db
    db.create_all()
    print(\"Database initialized\")
"
'
```

#### Step 8: Start Services
```bash
# Start and enable services
sudo systemctl start redis-server
sudo systemctl enable redis-server

sudo systemctl start supervisor
sudo systemctl enable supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start lanaim-pos

sudo systemctl start nginx
sudo systemctl enable nginx
```

## SSL/HTTPS Setup (Recommended)

### Using Let's Encrypt (Free)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add line: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Using Custom SSL Certificate
```bash
# Place your SSL files in /etc/ssl/
sudo cp your-certificate.crt /etc/ssl/certs/
sudo cp your-private-key.key /etc/ssl/private/

# Update Nginx configuration to use SSL
```

## Production Configuration

### Environment Variables
Edit `/etc/lanaim-pos/production.env`:

```bash
# Core Settings
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///opt/lanaim-pos/instance/lanaim_production.db

# Redis Settings
REDIS_URL=redis://localhost:6379/0

# Security Settings
SECURITY_ENABLED=true
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5
RATE_LIMIT_ENABLED=true

# Backup Settings
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=daily

# Monitoring Settings
MONITORING_ENABLED=true
LOG_LEVEL=INFO

# Email Settings (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Performance Settings
WORKERS=4
WORKER_CLASS=eventlet
WORKER_CONNECTIONS=1000
```

## Monitoring and Maintenance

### Health Checks
```bash
# Application health
curl http://your-domain.com/health

# Service status
sudo supervisorctl status
sudo systemctl status nginx
sudo systemctl status redis-server
```

### Log Monitoring
```bash
# Application logs
tail -f /opt/lanaim-pos/logs/gunicorn.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# System logs
sudo journalctl -f -u supervisor
```

### Backup Management
```bash
# Manual backup
curl -X POST http://your-domain.com/admin/backup \
     -H "Authorization: Bearer your-admin-token"

# List backups
ls -la /opt/lanaim-pos/backups/

# Restore from backup
# (Use the backup restoration functionality in the admin panel)
```

### Performance Monitoring
Access the admin panel at `http://your-domain.com/admin/system-status` to view:
- System resource usage
- Request statistics
- Cache performance
- Database metrics
- Security events

## Security Best Practices

### 1. Regular Updates
```bash
# Update system packages monthly
sudo apt update && sudo apt upgrade -y

# Update Python packages
sudo -u lanaim /opt/lanaim-pos/venv/bin/pip list --outdated
```

### 2. Backup Strategy
- Automated daily backups enabled
- Keep 30 days of backups
- Test restore procedures monthly
- Store backups off-site

### 3. Monitoring
- Monitor system resources
- Set up alerts for high CPU/memory usage
- Monitor application logs for errors
- Track security events

### 4. Access Control
- Use strong passwords
- Enable two-factor authentication
- Limit admin access
- Regular user access reviews

## Troubleshooting

### Common Issues

1. **Application won't start**:
```bash
# Check logs
sudo supervisorctl tail lanaim-pos

# Check configuration
sudo supervisorctl status
```

2. **Nginx 502 errors**:
```bash
# Check if application is running
curl http://127.0.0.1:8000/health

# Restart application
sudo supervisorctl restart lanaim-pos
```

3. **Database errors**:
```bash
# Check database file permissions
ls -la /opt/lanaim-pos/instance/

# Reinitialize database if needed
sudo -u lanaim /opt/lanaim-pos/venv/bin/python3 -c "
from app_production import create_production_app
app = create_production_app()
with app.app_context():
    from models import db
    db.create_all()
"
```

4. **Redis connection issues**:
```bash
# Check Redis status
sudo systemctl status redis-server

# Test Redis connection
redis-cli ping
```

### Emergency Procedures

1. **Complete service restart**:
```bash
sudo supervisorctl restart lanaim-pos
sudo systemctl restart nginx
sudo systemctl restart redis-server
```

2. **Rollback deployment**:
```bash
# Stop services
sudo supervisorctl stop lanaim-pos

# Restore from backup
# (Use backup restoration process)

# Start services
sudo supervisorctl start lanaim-pos
```

## Support and Updates

### Version Updates
1. Test updates in staging environment
2. Create backup before updating
3. Follow semantic versioning
4. Document changes in changelog

### Getting Help
- Check logs first
- Review this documentation
- Contact development team
- Submit issues via project repository

## Performance Optimization

### Database Optimization
- Regular VACUUM operations
- Index optimization
- Query performance monitoring

### Caching Strategy
- Redis caching for frequently accessed data
- Static file caching via Nginx
- Database query result caching

### Resource Monitoring
- CPU and memory usage tracking
- Disk space monitoring
- Network performance monitoring
- Application response time tracking

This completes the production deployment guide for LanAim POS v5.3. The system is now ready for production use with comprehensive security, monitoring, and backup capabilities.
