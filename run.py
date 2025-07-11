"""
LanAim POS System v2.4 - Phase 1
Main Application Runner

Run this file to start the LanAim POS system.
"""

from app import app, socketio
from utils import register_template_filters

# Register template filters
register_template_filters(app)

if __name__ == '__main__':
    print("🍽️  Starting LanAim POS System v2.4 - Phase 1")
    print("=" * 50)
    print("📊 Customer Interface: http://localhost:5001")
    print("👨‍🍳 Staff Kitchen: http://localhost:5001/staff")
    print("🚚 Staff Delivery: http://localhost:5001/staff")
    print("=" * 50)
    print("\n📋 Demo Accounts:")
    print("   Kitchen Staff: kitchen / kitchen123")
    print("   Delivery Staff: delivery / delivery123")
    print("\n🔧 Features in Phase 1:")
    print("   ✅ Menu browsing and ordering")
    print("   ✅ Cart management")
    print("   ✅ Order tracking")
    print("   ✅ Staff order management")
    print("   ✅ Real-time notifications (basic)")
    print("   ✅ Feedback system")
    print("\n🚀 Starting server...")
    
    # Run with SocketIO support
    socketio.run(
        app,
        host='0.0.0.0',
        port=5001,
        debug=True,
        allow_unsafe_werkzeug=True  # For development only
    )
