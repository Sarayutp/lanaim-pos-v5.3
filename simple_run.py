#!/usr/bin/env python3
"""
Simple Flask server runner without SocketIO
สำหรับเทสการเริ่มต้นเซิร์ฟเวอร์
"""

from app import app

if __name__ == '__main__':
    print("🍽️  Starting LanAim POS System - Simple Mode")
    print("=" * 50)
    print("📊 Customer Interface: http://localhost:5001")
    print("🔧 Admin Dashboard: http://localhost:5001/admin")
    print("👨‍🍳 Staff: http://localhost:5001/staff")
    print("=" * 50)
    print("🚀 Starting simple Flask server...")
    
    # Run simple Flask app without SocketIO
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=True,
        use_reloader=False  # ปิด reloader เพื่อลด complexity
    )