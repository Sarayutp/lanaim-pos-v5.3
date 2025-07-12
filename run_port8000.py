#!/usr/bin/env python3
"""
Alternative port runner
"""

from app import app

if __name__ == '__main__':
    print("🍽️  Starting LanAim POS System - Port 8000")
    print("=" * 50)
    print("📊 Customer Interface: http://localhost:8000")
    print("🔧 Admin Dashboard: http://localhost:8000/admin")
    print("=" * 50)
    
    app.run(
        host='127.0.0.1',
        port=8000,
        debug=True,
        use_reloader=False
    )