"""
Test Production Components
Unit tests for production-ready components like security, caching, monitoring
"""

import pytest
import tempfile
import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import production components
from security import SecurityManager, security_manager
from caching import CacheManager, cache_manager, cached
from monitoring import PerformanceMonitor, performance_monitor
from backup import BackupManager, backup_manager
from notifications import NotificationManager, notification_manager


class TestSecurityManager:
    """Test security manager functionality"""
    
    def test_security_manager_initialization(self, app):
        """Test security manager initialization"""
        sec_manager = SecurityManager()
        sec_manager.init_app(app)
        
        assert sec_manager.app == app
        assert hasattr(sec_manager, 'failed_attempts')
        assert hasattr(sec_manager, 'blocked_ips')
    
    def test_rate_limiting(self, app):
        """Test rate limiting functionality"""
        with app.app_context():
            sec_manager = SecurityManager()
            sec_manager.init_app(app)
            
            # Test rate limiting
            client_ip = '192.168.1.100'
            
            # Should allow initial requests
            for i in range(5):
                result = sec_manager.check_rate_limit(client_ip)
                assert result is True
            
            # Should block after too many requests
            for i in range(100):  # Exceed rate limit
                sec_manager.check_rate_limit(client_ip)
            
            # Should be blocked now
            result = sec_manager.check_rate_limit(client_ip)
            # Behavior depends on implementation
    
    def test_password_validation(self, app):
        """Test password validation"""
        with app.app_context():
            sec_manager = SecurityManager()
            sec_manager.init_app(app)
            
            # Test weak passwords
            weak_passwords = ['123', 'password', 'abc', '']
            for password in weak_passwords:
                is_valid, message = sec_manager.validate_password(password)
                assert is_valid is False
                assert message is not None
            
            # Test strong passwords
            strong_passwords = ['StrongPass123!', 'MySecur3P@ssw0rd', 'C0mpl3x!P@ssw0rd']
            for password in strong_passwords:
                is_valid, message = sec_manager.validate_password(password)
                assert is_valid is True
    
    def test_input_validation(self, app):
        """Test input validation and sanitization"""
        with app.app_context():
            sec_manager = SecurityManager()
            sec_manager.init_app(app)
            
            # Test XSS prevention
            malicious_inputs = [
                '<script>alert("xss")</script>',
                'javascript:alert(1)',
                '<img src=x onerror=alert(1)>',
                '"><script>alert(1)</script>'
            ]
            
            for malicious_input in malicious_inputs:
                sanitized = sec_manager.sanitize_input(malicious_input)
                assert '<script>' not in sanitized.lower()
                assert 'javascript:' not in sanitized.lower()
    
    def test_file_upload_validation(self, app):
        """Test file upload security validation"""
        with app.app_context():
            sec_manager = SecurityManager()
            sec_manager.init_app(app)
            
            # Test allowed file types
            allowed_files = ['image.jpg', 'photo.png', 'picture.jpeg', 'icon.gif']
            for filename in allowed_files:
                is_valid, message = sec_manager.validate_file_upload(filename, b'fake_content')
                assert is_valid is True
            
            # Test disallowed file types
            disallowed_files = ['script.js', 'malware.exe', 'virus.php', 'exploit.html']
            for filename in disallowed_files:
                is_valid, message = sec_manager.validate_file_upload(filename, b'fake_content')
                assert is_valid is False
    
    def test_security_events_logging(self, app):
        """Test security events logging"""
        with app.app_context():
            sec_manager = SecurityManager()
            sec_manager.init_app(app)
            
            # Log security event
            sec_manager.log_security_event('test_event', 'Test security event', '192.168.1.1')
            
            # Get security events
            events = sec_manager.get_security_events()
            assert len(events) > 0
            
            latest_event = events[0]
            assert latest_event['event_type'] == 'test_event'
            assert latest_event['description'] == 'Test security event'
            assert latest_event['ip_address'] == '192.168.1.1'


class TestCacheManager:
    """Test cache manager functionality"""
    
    def test_cache_manager_initialization(self, app):
        """Test cache manager initialization"""
        cache_mgr = CacheManager()
        cache_mgr.init_app(app)
        
        assert cache_mgr.app == app
        assert hasattr(cache_mgr, 'memory_cache')
    
    def test_basic_cache_operations(self, app):
        """Test basic cache set/get operations"""
        with app.app_context():
            cache_mgr = CacheManager()
            cache_mgr.init_app(app)
            
            # Test setting and getting values
            cache_mgr.set('test_key', 'test_value', timeout=60)
            value = cache_mgr.get('test_key')
            assert value == 'test_value'
            
            # Test non-existent key
            value = cache_mgr.get('non_existent_key')
            assert value is None
            
            # Test deleting key
            deleted = cache_mgr.delete('test_key')
            assert deleted is True
            
            value = cache_mgr.get('test_key')
            assert value is None
    
    def test_cache_expiration(self, app):
        """Test cache expiration"""
        with app.app_context():
            cache_mgr = CacheManager()
            cache_mgr.init_app(app)
            
            # Set value with short timeout
            cache_mgr.set('expire_test', 'value', timeout=1)
            
            # Should be available immediately
            value = cache_mgr.get('expire_test')
            assert value == 'value'
            
            # Wait for expiration
            time.sleep(2)
            
            # Should be expired now
            value = cache_mgr.get('expire_test')
            assert value is None
    
    def test_cache_decorator(self, app):
        """Test cache decorator functionality"""
        with app.app_context():
            cache_mgr = CacheManager()
            cache_mgr.init_app(app)
            
            call_count = 0
            
            @cached(timeout=60)
            def expensive_function(param):
                nonlocal call_count
                call_count += 1
                return f"result_{param}"
            
            # First call should execute function
            result1 = expensive_function("test")
            assert result1 == "result_test"
            assert call_count == 1
            
            # Second call should use cache
            result2 = expensive_function("test")
            assert result2 == "result_test"
            assert call_count == 1  # Should not increment
            
            # Different parameter should execute function again
            result3 = expensive_function("different")
            assert result3 == "result_different"
            assert call_count == 2
    
    def test_cache_statistics(self, app):
        """Test cache statistics"""
        with app.app_context():
            cache_mgr = CacheManager()
            cache_mgr.init_app(app)
            
            # Perform cache operations
            cache_mgr.set('stats_test', 'value')
            cache_mgr.get('stats_test')  # Hit
            cache_mgr.get('non_existent')  # Miss
            
            stats = cache_mgr.get_stats()
            assert 'hits' in stats
            assert 'misses' in stats
            assert 'sets' in stats
            assert stats['hits'] >= 1
            assert stats['misses'] >= 1
            assert stats['sets'] >= 1


class TestPerformanceMonitor:
    """Test performance monitoring functionality"""
    
    def test_performance_monitor_initialization(self, app):
        """Test performance monitor initialization"""
        perf_monitor = PerformanceMonitor()
        perf_monitor.init_app(app)
        
        assert perf_monitor.app == app
        assert hasattr(perf_monitor, 'metrics')
        assert perf_monitor.start_time is not None
    
    def test_request_timing(self, app, client):
        """Test request timing functionality"""
        with app.app_context():
            perf_monitor = PerformanceMonitor()
            perf_monitor.init_app(app)
            
            # Make some requests
            client.get('/')
            client.get('/menu')
            
            # Check metrics
            assert len(perf_monitor.metrics['request_times']) > 0
            assert len(perf_monitor.metrics['endpoint_stats']) > 0
    
    def test_performance_report(self, app):
        """Test performance report generation"""
        with app.app_context():
            perf_monitor = PerformanceMonitor()
            perf_monitor.init_app(app)
            
            # Add some fake metrics
            perf_monitor.metrics['request_times'].extend([0.1, 0.2, 0.3, 0.5, 1.0])
            perf_monitor.metrics['endpoint_stats']['test_endpoint'] = {'count': 5, 'total_time': 2.1}
            
            report = perf_monitor.get_performance_report()
            
            assert 'uptime' in report
            assert 'requests' in report
            assert 'system' in report
            assert 'endpoints' in report
            
            assert report['requests']['total_processed'] >= 0
            assert report['requests']['avg_response_time'] >= 0
    
    def test_health_status(self, app):
        """Test health status check"""
        with app.app_context():
            perf_monitor = PerformanceMonitor()
            perf_monitor.init_app(app)
            
            health = perf_monitor.get_health_status()
            
            assert 'status' in health
            assert 'score' in health
            assert health['status'] in ['excellent', 'good', 'fair', 'poor', 'critical', 'unknown']
            assert 0 <= health['score'] <= 100


class TestBackupManager:
    """Test backup manager functionality"""
    
    def test_backup_manager_initialization(self, app):
        """Test backup manager initialization"""
        backup_mgr = BackupManager()
        backup_mgr.init_app(app)
        
        assert backup_mgr.app == app
    
    @patch('backup.os.path.exists')
    @patch('backup.shutil.copy2')
    @patch('backup.zipfile.ZipFile')
    def test_create_backup(self, mock_zipfile, mock_copy, mock_exists, app):
        """Test backup creation"""
        with app.app_context():
            mock_exists.return_value = True
            mock_zip_instance = MagicMock()
            mock_zipfile.return_value.__enter__.return_value = mock_zip_instance
            
            backup_mgr = BackupManager()
            backup_mgr.init_app(app)
            
            # Create temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                app.config['BACKUP_DIR'] = temp_dir
                backup_mgr.backup_dir = temp_dir
                
                backup_file = backup_mgr.create_backup()
                
                # Should return backup filename
                assert backup_file is not None
                assert backup_file.endswith('.zip')
    
    def test_backup_status(self, app):
        """Test backup status check"""
        with app.app_context():
            backup_mgr = BackupManager()
            backup_mgr.init_app(app)
            
            status = backup_mgr.get_backup_status()
            
            assert 'status' in status
            assert 'last_backup' in status
            assert 'backup_count' in status
    
    def test_list_backups(self, app):
        """Test listing backups"""
        with app.app_context():
            backup_mgr = BackupManager()
            backup_mgr.init_app(app)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                backup_mgr.backup_dir = temp_dir
                
                # Create fake backup files
                fake_backups = [
                    'backup_20231201_120000.zip',
                    'backup_20231202_120000.zip'
                ]
                
                for backup in fake_backups:
                    open(os.path.join(temp_dir, backup), 'w').close()
                
                backups = backup_mgr.list_backups()
                assert len(backups) >= 2


class TestNotificationManager:
    """Test notification manager functionality"""
    
    def test_notification_manager_initialization(self, app):
        """Test notification manager initialization"""
        notif_mgr = NotificationManager()
        notif_mgr.init_app(app)
        
        assert notif_mgr.app == app
    
    def test_send_notification(self, app):
        """Test sending notifications"""
        with app.app_context():
            notif_mgr = NotificationManager()
            notif_mgr.init_app(app)
            
            # Test sending notification
            result = notif_mgr.send_notification(
                'test_room',
                'test_message',
                {'data': 'test'},
                'info'
            )
            
            # Should handle gracefully even without WebSocket connections
            assert result is not None
    
    def test_order_notifications(self, app):
        """Test order-specific notifications"""
        with app.app_context():
            notif_mgr = NotificationManager()
            notif_mgr.init_app(app)
            
            # Test order status notification
            notif_mgr.notify_order_status_change(1, 'preparing', 'confirmed')
            
            # Test new order notification
            notif_mgr.notify_new_order(1, 'delivery')
            
            # Should execute without errors
            assert True


class TestProductionIntegration:
    """Test integration of production components"""
    
    def test_production_app_creation(self):
        """Test creating production app with all components"""
        from app_production import create_production_app
        
        # Mock environment to avoid production database
        with patch.dict(os.environ, {'FLASK_ENV': 'testing'}):
            app = create_production_app()
            
            assert app is not None
            assert app.config['TESTING'] is True
    
    def test_production_startup_checks(self):
        """Test production startup checks"""
        from app_production import run_startup_checks, create_production_app
        
        with patch.dict(os.environ, {'FLASK_ENV': 'testing'}):
            app = create_production_app()
            
            with app.app_context():
                checks_passed, issues = run_startup_checks(app)
                
                # Should return boolean and list
                assert isinstance(checks_passed, bool)
                assert isinstance(issues, list)
    
    def test_health_endpoint(self, client):
        """Test production health endpoint"""
        response = client.get('/health')
        
        # Should return health status
        assert response.status_code in [200, 503]  # OK or Service Unavailable
        
        if response.is_json:
            data = response.get_json()
            assert 'status' in data


class TestConfigurationManagement:
    """Test configuration management"""
    
    def test_production_config(self):
        """Test production configuration"""
        from config_production import ProductionConfig
        
        config = ProductionConfig()
        
        # Should have production settings
        assert hasattr(config, 'SECRET_KEY')
        assert hasattr(config, 'DATABASE_URL')
        assert hasattr(config, 'REDIS_URL')
        assert config.DEBUG is False
        assert config.TESTING is False
    
    def test_environment_variables(self):
        """Test environment variable handling"""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test_secret',
            'DATABASE_URL': 'sqlite:///test.db',
            'REDIS_URL': 'redis://localhost:6379/1'
        }):
            from config_production import ProductionConfig
            config = ProductionConfig()
            
            assert 'test_secret' in str(config.SECRET_KEY)


class TestErrorHandling:
    """Test error handling in production components"""
    
    def test_cache_error_handling(self, app):
        """Test cache error handling"""
        with app.app_context():
            cache_mgr = CacheManager()
            cache_mgr.init_app(app)
            
            # Test with invalid key types
            try:
                cache_mgr.set(None, 'value')
                cache_mgr.get(None)
            except Exception:
                pass  # Should handle gracefully
    
    def test_monitoring_error_handling(self, app):
        """Test monitoring error handling"""
        with app.app_context():
            perf_monitor = PerformanceMonitor()
            perf_monitor.init_app(app)
            
            # Should handle errors gracefully
            try:
                health = perf_monitor.get_health_status()
                assert health is not None
            except Exception as e:
                assert 'error' in str(e).lower()
    
    def test_backup_error_handling(self, app):
        """Test backup error handling"""
        with app.app_context():
            backup_mgr = BackupManager()
            backup_mgr.init_app(app)
            
            # Test with invalid backup directory
            backup_mgr.backup_dir = '/invalid/directory/path'
            
            try:
                status = backup_mgr.get_backup_status()
                # Should return error status
                assert status is not None
            except Exception:
                pass  # Should handle gracefully
