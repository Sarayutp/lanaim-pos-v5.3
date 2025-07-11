"""
Caching System for Performance Optimization
Redis-based caching with fallback to in-memory caching
"""

import json
import pickle
import hashlib
from datetime import datetime, timedelta
from functools import wraps
import logging

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

class CacheManager:
    """Handles caching operations with Redis fallback to memory"""
    
    def __init__(self, app=None):
        self.app = app
        self.redis_client = None
        self.memory_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
    def init_app(self, app):
        """Initialize cache manager with Flask app"""
        self.app = app
        
        # Try to connect to Redis
        redis_url = app.config.get('REDIS_URL')
        if redis_url and redis_url != 'memory://' and redis:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Redis connected for caching")
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache: {e}")
                self.redis_client = None
        else:
            logger.info("Using in-memory cache")
    
    def _make_key(self, key):
        """Create a consistent cache key"""
        if isinstance(key, str):
            return f"lanaim_cache:{key}"
        else:
            # Hash complex keys
            key_str = json.dumps(key, sort_keys=True)
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"lanaim_cache:{key_hash}"
    
    def get(self, key):
        """Get value from cache"""
        cache_key = self._make_key(key)
        
        try:
            if self.redis_client:
                # Try Redis first
                value = self.redis_client.get(cache_key)
                if value:
                    self.cache_stats['hits'] += 1
                    return pickle.loads(value)
            else:
                # Use memory cache
                if cache_key in self.memory_cache:
                    cached_item = self.memory_cache[cache_key]
                    
                    # Check expiration
                    if cached_item['expires_at'] > datetime.now():
                        self.cache_stats['hits'] += 1
                        return cached_item['value']
                    else:
                        # Remove expired item
                        del self.memory_cache[cache_key]
            
            self.cache_stats['misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, key, value, timeout=3600):
        """Set value in cache with timeout in seconds"""
        cache_key = self._make_key(key)
        
        try:
            if self.redis_client:
                # Use Redis
                pickled_value = pickle.dumps(value)
                self.redis_client.setex(cache_key, timeout, pickled_value)
            else:
                # Use memory cache
                expires_at = datetime.now() + timedelta(seconds=timeout)
                self.memory_cache[cache_key] = {
                    'value': value,
                    'expires_at': expires_at
                }
                
                # Clean old items from memory cache
                self._cleanup_memory_cache()
            
            self.cache_stats['sets'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key):
        """Delete value from cache"""
        cache_key = self._make_key(key)
        
        try:
            if self.redis_client:
                result = self.redis_client.delete(cache_key)
                deleted = result > 0
            else:
                deleted = cache_key in self.memory_cache
                if deleted:
                    del self.memory_cache[cache_key]
            
            if deleted:
                self.cache_stats['deletes'] += 1
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear(self):
        """Clear all cache"""
        try:
            if self.redis_client:
                # Delete all keys with our prefix
                keys = self.redis_client.keys("lanaim_cache:*")
                if keys:
                    self.redis_client.delete(*keys)
            else:
                self.memory_cache.clear()
            
            logger.info("Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """Remove expired items from memory cache"""
        if len(self.memory_cache) > 1000:  # Cleanup when cache gets large
            now = datetime.now()
            expired_keys = [
                key for key, item in self.memory_cache.items()
                if item['expires_at'] <= now
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
    
    def get_stats(self):
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'sets': self.cache_stats['sets'],
            'deletes': self.cache_stats['deletes'],
            'hit_rate': round(hit_rate, 2),
            'backend': 'Redis' if self.redis_client else 'Memory',
            'memory_cache_size': len(self.memory_cache)
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats['redis_memory'] = info.get('used_memory_human', 'Unknown')
                stats['redis_keys'] = info.get('db0', {}).get('keys', 0)
            except:
                pass
        
        return stats

# Global cache manager instance
cache_manager = CacheManager()

def cached(timeout=3600, key_func=None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Use function name and arguments as key
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator

def cache_menu_items(timeout=1800):  # 30 minutes
    """Cache decorator specifically for menu items"""
    return cached(timeout=timeout, key_func=lambda *args, **kwargs: "menu_items")

def cache_delivery_zones(timeout=3600):  # 1 hour
    """Cache decorator for delivery zones"""
    return cached(timeout=timeout, key_func=lambda *args, **kwargs: "delivery_zones")

def cache_analytics_data(timeout=300):  # 5 minutes
    """Cache decorator for analytics data"""
    def key_func(*args, **kwargs):
        # Include parameters in cache key for analytics
        parts = ["analytics"]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(parts)
    
    return cached(timeout=timeout, key_func=key_func)

def invalidate_menu_cache():
    """Invalidate menu-related cache"""
    cache_manager.delete("menu_items")
    cache_manager.delete("delivery_zones")
    logger.info("Menu cache invalidated")

def invalidate_analytics_cache():
    """Invalidate analytics cache"""
    # Delete all analytics cache keys
    if cache_manager.redis_client:
        try:
            keys = cache_manager.redis_client.keys("lanaim_cache:analytics*")
            if keys:
                cache_manager.redis_client.delete(*keys)
        except:
            pass
    else:
        # For memory cache, we need to find and delete analytics keys
        analytics_keys = [
            key for key in cache_manager.memory_cache.keys()
            if 'analytics' in key
        ]
        for key in analytics_keys:
            del cache_manager.memory_cache[key]
    
    logger.info("Analytics cache invalidated")
