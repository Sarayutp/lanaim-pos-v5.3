"""
Performance Monitoring System
Track system performance and generate optimization reports
"""

import time
import psutil
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, deque
import threading
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor system performance and track metrics"""
    
    def __init__(self, app=None):
        self.app = app
        self.metrics = {
            'request_times': deque(maxlen=1000),
            'endpoint_stats': defaultdict(lambda: {'count': 0, 'total_time': 0}),
            'error_counts': defaultdict(int),
            'memory_usage': deque(maxlen=100),
            'cpu_usage': deque(maxlen=100),
            'active_connections': 0
        }
        self.start_time = datetime.now()
        self.monitoring_active = False
        self.monitoring_thread = None
        
    def init_app(self, app):
        """Initialize performance monitor with Flask app"""
        self.app = app
        
        # Register request hooks
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_request(self.teardown_request)
        
        # Start background monitoring
        self.start_monitoring()
        
    def start_monitoring(self):
        """Start background system monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitor_system,
                daemon=True
            )
            self.monitoring_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def before_request(self):
        """Record request start time"""
        from flask import g
        g.start_time = time.time()
        self.metrics['active_connections'] += 1
    
    def after_request(self, response):
        """Record request completion"""
        from flask import g, request
        
        if hasattr(g, 'start_time'):
            request_time = time.time() - g.start_time
            self.metrics['request_times'].append(request_time)
            
            # Track endpoint statistics
            endpoint = request.endpoint or 'unknown'
            self.metrics['endpoint_stats'][endpoint]['count'] += 1
            self.metrics['endpoint_stats'][endpoint]['total_time'] += request_time
            
            # Log slow requests
            if request_time > 5.0:  # Slow request threshold
                logger.warning(f"Slow request: {endpoint} took {request_time:.2f}s")
        
        return response
    
    def teardown_request(self, exception):
        """Handle request teardown"""
        self.metrics['active_connections'] = max(0, self.metrics['active_connections'] - 1)
        
        if exception:
            error_type = type(exception).__name__
            self.metrics['error_counts'][error_type] += 1
    
    def _monitor_system(self):
        """Background thread to monitor system resources"""
        while self.monitoring_active:
            try:
                # Monitor memory usage
                memory_percent = psutil.virtual_memory().percent
                self.metrics['memory_usage'].append({
                    'timestamp': datetime.now(),
                    'percent': memory_percent
                })
                
                # Monitor CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics['cpu_usage'].append({
                    'timestamp': datetime.now(),
                    'percent': cpu_percent
                })
                
                # Log warnings for high resource usage
                if memory_percent > 85:
                    logger.warning(f"High memory usage: {memory_percent}%")
                
                if cpu_percent > 80:
                    logger.warning(f"High CPU usage: {cpu_percent}%")
                
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def get_performance_report(self):
        """Generate comprehensive performance report"""
        now = datetime.now()
        uptime = now - self.start_time
        
        # Calculate request statistics
        request_times = list(self.metrics['request_times'])
        if request_times:
            avg_response_time = sum(request_times) / len(request_times)
            max_response_time = max(request_times)
            min_response_time = min(request_times)
            # Calculate 95th percentile
            sorted_times = sorted(request_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[p95_index] if sorted_times else 0
        else:
            avg_response_time = max_response_time = min_response_time = p95_response_time = 0
        
        # Top slow endpoints
        slow_endpoints = sorted(
            self.metrics['endpoint_stats'].items(),
            key=lambda x: x[1]['total_time'] / x[1]['count'] if x[1]['count'] > 0 else 0,
            reverse=True
        )[:5]
        
        # Most popular endpoints
        popular_endpoints = sorted(
            self.metrics['endpoint_stats'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        # Current system resources
        current_memory = psutil.virtual_memory().percent
        current_cpu = psutil.cpu_percent()
        disk_usage = psutil.disk_usage('/').percent
        
        # Recent averages
        recent_memory = list(self.metrics['memory_usage'])[-10:]  # Last 10 readings
        recent_cpu = list(self.metrics['cpu_usage'])[-10:]
        
        avg_memory = sum(m['percent'] for m in recent_memory) / len(recent_memory) if recent_memory else 0
        avg_cpu = sum(c['percent'] for c in recent_cpu) / len(recent_cpu) if recent_cpu else 0
        
        report = {
            'uptime': str(uptime),
            'uptime_seconds': uptime.total_seconds(),
            'current_time': now.isoformat(),
            
            # Request metrics
            'requests': {
                'total_processed': sum(stats['count'] for stats in self.metrics['endpoint_stats'].values()),
                'active_connections': self.metrics['active_connections'],
                'avg_response_time': round(avg_response_time, 3),
                'max_response_time': round(max_response_time, 3),
                'min_response_time': round(min_response_time, 3),
                'p95_response_time': round(p95_response_time, 3),
            },
            
            # System resources
            'system': {
                'memory_percent': current_memory,
                'cpu_percent': current_cpu,
                'disk_percent': disk_usage,
                'avg_memory_10min': round(avg_memory, 1),
                'avg_cpu_10min': round(avg_cpu, 1),
            },
            
            # Endpoint performance
            'endpoints': {
                'slowest': [
                    {
                        'endpoint': endpoint,
                        'avg_time': round(stats['total_time'] / stats['count'], 3),
                        'count': stats['count']
                    }
                    for endpoint, stats in slow_endpoints
                ],
                'most_popular': [
                    {
                        'endpoint': endpoint,
                        'count': stats['count'],
                        'avg_time': round(stats['total_time'] / stats['count'], 3)
                    }
                    for endpoint, stats in popular_endpoints
                ]
            },
            
            # Error statistics
            'errors': dict(self.metrics['error_counts']),
            'total_errors': sum(self.metrics['error_counts'].values())
        }
        
        return report
    
    def get_health_status(self):
        """Get system health status"""
        try:
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent()
            disk_percent = psutil.disk_usage('/').percent
            
            # Calculate health score
            health_score = 100
            
            if memory_percent > 90:
                health_score -= 30
            elif memory_percent > 80:
                health_score -= 15
            elif memory_percent > 70:
                health_score -= 5
            
            if cpu_percent > 90:
                health_score -= 25
            elif cpu_percent > 80:
                health_score -= 10
            elif cpu_percent > 70:
                health_score -= 5
            
            if disk_percent > 95:
                health_score -= 20
            elif disk_percent > 85:
                health_score -= 10
            
            # Check error rate
            total_requests = sum(stats['count'] for stats in self.metrics['endpoint_stats'].values())
            total_errors = sum(self.metrics['error_counts'].values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            
            if error_rate > 10:
                health_score -= 20
            elif error_rate > 5:
                health_score -= 10
            
            # Determine status
            if health_score >= 90:
                status = 'excellent'
            elif health_score >= 75:
                status = 'good'
            elif health_score >= 60:
                status = 'fair'
            elif health_score >= 40:
                status = 'poor'
            else:
                status = 'critical'
            
            return {
                'status': status,
                'score': max(0, health_score),
                'memory_percent': memory_percent,
                'cpu_percent': cpu_percent,
                'disk_percent': disk_percent,
                'error_rate': round(error_rate, 2),
                'active_connections': self.metrics['active_connections'],
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                'status': 'unknown',
                'score': 0,
                'error': str(e)
            }

def performance_timer(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    return wrapper

def database_performance_check(db_path):
    """Check database performance metrics"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get database size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size = cursor.fetchone()[0]
        
        # Get table information
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_stats = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_stats[table] = count
        
        # Check for missing indexes (simple heuristic)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'database_size': db_size,
            'database_size_mb': round(db_size / (1024 * 1024), 2),
            'table_counts': table_stats,
            'total_records': sum(table_stats.values()),
            'indexes': len(indexes),
            'tables': len(tables)
        }
        
    except Exception as e:
        logger.error(f"Database performance check error: {e}")
        return {'error': str(e)}

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
