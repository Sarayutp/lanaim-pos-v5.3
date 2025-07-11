"""
Real-time Notification System using WebSocket
Production-ready WebSocket implementation with Redis support
"""

from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request
from flask_login import current_user
import json
try:
    import redis
except ImportError:
    redis = None
import logging
from datetime import datetime
from models import db, Order, User

logger = logging.getLogger(__name__)

class NotificationManager:
    """Handles real-time notifications via WebSocket"""
    
    def __init__(self, app=None, socketio=None):
        self.app = app
        self.socketio = socketio
        self.redis_client = None
        self.connected_users = {}
        
    def init_app(self, app, socketio):
        """Initialize notification manager"""
        self.app = app
        self.socketio = socketio
        
        # Initialize Redis for message persistence (optional)
        redis_url = app.config.get('REDIS_URL')
        if redis_url and redis_url != 'memory://' and redis:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("Redis connected for notifications")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None
        
        # Register SocketIO event handlers
        self.register_handlers()
        
    def register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            if current_user.is_authenticated:
                user_id = current_user.id
                user_role = getattr(current_user, 'role', 'customer')
                
                # Store user connection info
                self.connected_users[request.sid] = {
                    'user_id': user_id,
                    'role': user_role,
                    'connected_at': datetime.now(),
                    'username': getattr(current_user, 'username', 'Unknown')
                }
                
                # Join role-based room
                join_room(f"role_{user_role}")
                
                # Join user-specific room
                join_room(f"user_{user_id}")
                
                logger.info(f"User {current_user.username} ({user_role}) connected")
                
                # Send connection confirmation
                emit('connected', {
                    'message': 'Connected to notification service',
                    'role': user_role,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Send any pending notifications
                self.send_pending_notifications(user_id)
                
            else:
                # Allow anonymous connections for order tracking
                emit('connected', {
                    'message': 'Connected as guest',
                    'role': 'guest',
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            if request.sid in self.connected_users:
                user_info = self.connected_users[request.sid]
                logger.info(f"User {user_info['username']} disconnected")
                del self.connected_users[request.sid]
        
        @self.socketio.on('join_order_tracking')
        def handle_join_order_tracking(data):
            """Join order-specific room for tracking"""
            order_number = data.get('order_number')
            if order_number:
                join_room(f"order_{order_number}")
                emit('joined_order_tracking', {
                    'order_number': order_number,
                    'message': f'Now tracking order {order_number}'
                })
        
        @self.socketio.on('leave_order_tracking')
        def handle_leave_order_tracking(data):
            """Leave order tracking room"""
            order_number = data.get('order_number')
            if order_number:
                leave_room(f"order_{order_number}")
                emit('left_order_tracking', {
                    'order_number': order_number
                })
        
        @self.socketio.on('staff_status_update')
        def handle_staff_status_update(data):
            """Handle staff status updates"""
            if current_user.is_authenticated and hasattr(current_user, 'role'):
                if current_user.role in ['kitchen_staff', 'delivery_staff', 'admin']:
                    status = data.get('status')
                    self.broadcast_staff_status_update(current_user.id, status)
    
    def send_new_order_notification(self, order):
        """Send new order notification to kitchen staff"""
        try:
            notification_data = {
                'type': 'new_order',
                'order_id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'total_amount': float(order.total_amount),
                'items_count': len(order.items),
                'created_at': order.created_at.isoformat(),
                'message': f'New order {order.order_number} received',
                'timestamp': datetime.now().isoformat(),
                'sound': 'new_order.mp3'
            }
            
            # Send to kitchen staff
            self.socketio.emit('new_order', notification_data, room='role_kitchen_staff')
            
            # Send to admin
            self.socketio.emit('new_order', notification_data, room='role_admin')
            
            # Store notification in Redis for persistence
            self.store_notification('kitchen_staff', notification_data)
            
            logger.info(f"New order notification sent: {order.order_number}")
            
        except Exception as e:
            logger.error(f"Failed to send new order notification: {e}")
    
    def send_order_status_update(self, order, old_status=None):
        """Send order status update notification"""
        try:
            notification_data = {
                'type': 'order_status_update',
                'order_id': order.id,
                'order_number': order.order_number,
                'old_status': old_status,
                'new_status': order.status,
                'status_text': self.get_status_text(order.status),
                'customer_name': order.customer_name,
                'updated_at': order.updated_at.isoformat(),
                'message': f'Order {order.order_number} is now {self.get_status_text(order.status)}',
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to customer tracking this order
            self.socketio.emit('order_status_update', notification_data, room=f'order_{order.order_number}')
            
            # Send to appropriate staff based on status
            if order.status == 'ready':
                # Notify delivery staff
                notification_data['sound'] = 'order_ready.mp3'
                self.socketio.emit('order_ready', notification_data, room='role_delivery_staff')
                self.store_notification('delivery_staff', notification_data)
            elif order.status == 'delivering':
                # Notify customer
                notification_data['sound'] = 'order_out_for_delivery.mp3'
                self.socketio.emit('order_out_for_delivery', notification_data, room=f'order_{order.order_number}')
            
            # Always notify admin
            self.socketio.emit('order_status_update', notification_data, room='role_admin')
            
            logger.info(f"Order status update sent: {order.order_number} -> {order.status}")
            
        except Exception as e:
            logger.error(f"Failed to send order status update: {e}")
    
    def send_kitchen_notification(self, message, order_id=None, sound=None):
        """Send notification to kitchen staff"""
        try:
            notification_data = {
                'type': 'kitchen_notification',
                'message': message,
                'order_id': order_id,
                'timestamp': datetime.now().isoformat(),
                'sound': sound or 'notification.mp3'
            }
            
            self.socketio.emit('kitchen_notification', notification_data, room='role_kitchen_staff')
            self.store_notification('kitchen_staff', notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send kitchen notification: {e}")
    
    def send_delivery_notification(self, message, order_id=None, sound=None):
        """Send notification to delivery staff"""
        try:
            notification_data = {
                'type': 'delivery_notification',
                'message': message,
                'order_id': order_id,
                'timestamp': datetime.now().isoformat(),
                'sound': sound or 'notification.mp3'
            }
            
            self.socketio.emit('delivery_notification', notification_data, room='role_delivery_staff')
            self.store_notification('delivery_staff', notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send delivery notification: {e}")
    
    def broadcast_staff_status_update(self, user_id, status):
        """Broadcast staff status update"""
        try:
            user = User.query.get(user_id)
            if user:
                notification_data = {
                    'type': 'staff_status_update',
                    'user_id': user_id,
                    'username': user.username,
                    'role': user.role,
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Send to all admin and staff
                self.socketio.emit('staff_status_update', notification_data, room='role_admin')
                self.socketio.emit('staff_status_update', notification_data, room='role_kitchen_staff')
                self.socketio.emit('staff_status_update', notification_data, room='role_delivery_staff')
                
        except Exception as e:
            logger.error(f"Failed to broadcast staff status update: {e}")
    
    def store_notification(self, role, notification_data):
        """Store notification in Redis for persistence"""
        if self.redis_client:
            try:
                key = f"notifications:{role}"
                # Keep last 50 notifications per role
                self.redis_client.lpush(key, json.dumps(notification_data))
                self.redis_client.ltrim(key, 0, 49)
                self.redis_client.expire(key, 86400)  # Expire in 24 hours
            except Exception as e:
                logger.error(f"Failed to store notification in Redis: {e}")
    
    def send_pending_notifications(self, user_id):
        """Send pending notifications to user"""
        if self.redis_client:
            try:
                user = User.query.get(user_id)
                if user and hasattr(user, 'role'):
                    key = f"notifications:{user.role}"
                    notifications = self.redis_client.lrange(key, 0, 9)  # Get last 10
                    
                    for notification_json in notifications:
                        notification_data = json.loads(notification_json)
                        notification_data['is_pending'] = True
                        self.socketio.emit('pending_notification', notification_data, room=f'user_{user_id}')
                        
            except Exception as e:
                logger.error(f"Failed to send pending notifications: {e}")
    
    def get_status_text(self, status):
        """Get human-readable status text"""
        status_map = {
            'pending': 'รอดำเนินการ',
            'confirmed': 'ยืนยันแล้ว',
            'preparing': 'กำลังเตรียม',
            'ready': 'พร้อมส่ง',
            'delivering': 'กำลังจัดส่ง',
            'delivered': 'จัดส่งแล้ว',
            'cancelled': 'ยกเลิก'
        }
        return status_map.get(status, status)
    
    def get_connected_users_stats(self):
        """Get statistics of connected users"""
        stats = {
            'total_connected': len(self.connected_users),
            'by_role': {},
            'users': []
        }
        
        for sid, user_info in self.connected_users.items():
            role = user_info['role']
            if role not in stats['by_role']:
                stats['by_role'][role] = 0
            stats['by_role'][role] += 1
            
            stats['users'].append({
                'username': user_info['username'],
                'role': role,
                'connected_at': user_info['connected_at'].isoformat()
            })
        
        return stats

# Global notification manager instance
notification_manager = NotificationManager()
