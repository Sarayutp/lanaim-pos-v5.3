#!/usr/bin/env python3
"""
Debug version of the main app
"""

import traceback
import sys

def create_debug_app():
    try:
        print("🔧 Loading Flask...")
        from flask import Flask
        
        print("🔧 Creating app...")
        app = Flask(__name__)
        
        print("🔧 Loading config...")
        from config import config
        app.config.from_object(config['development'])
        
        print("🔧 Loading models...")
        from models import db, init_db, User
        
        print("🔧 Initializing database...")
        db.init_app(app)
        
        print("🔧 Adding basic route...")
        @app.route('/')
        def index():
            return '''
            <h1>🍽️ LanAim POS System</h1>
            <p>เซิร์ฟเวอร์ทำงานได้แล้ว!</p>
            <ul>
                <li><a href="/menu">เมนู</a></li>
                <li><a href="/admin">แอดมิน</a></li>
                <li><a href="/staff">พนักงาน</a></li>
            </ul>
            '''
        
        @app.route('/menu')
        def menu():
            return {'status': 'OK', 'message': 'Menu endpoint working'}
            
        print("✅ Basic app created successfully!")
        return app
        
    except Exception as e:
        print(f"❌ Error creating app: {e}")
        traceback.print_exc()
        return None

if __name__ == '__main__':
    print("🚀 Starting debug server...")
    
    app = create_debug_app()
    if app:
        print("🔗 Open: http://127.0.0.1:8002")
        print("=" * 40)
        
        try:
            app.run(
                host='127.0.0.1',
                port=8002,
                debug=True,
                use_reloader=False
            )
        except Exception as e:
            print(f"❌ Server error: {e}")
            traceback.print_exc()
    else:
        print("❌ Failed to create app")
        sys.exit(1)