#!/usr/bin/env python3
"""
Minimal Flask test - เพื่อเทสว่า Flask ทำงานได้ไหม
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <h1>🍽️ LanAim POS - Test Server</h1>
    <p>เซิร์ฟเวอร์ทำงานได้แล้ว!</p>
    <ul>
        <li><a href="/test">Test Page</a></li>
        <li><a href="/status">Status</a></li>
    </ul>
    '''

@app.route('/test')
def test():
    return '<h2>✅ Test Page ทำงานได้!</h2>'

@app.route('/status')
def status():
    return {'status': 'OK', 'message': 'Server is running'}

if __name__ == '__main__':
    print("🚀 Starting minimal test server...")
    print("🔗 Open: http://127.0.0.1:8001")
    print("=" * 40)
    
    app.run(
        host='127.0.0.1',
        port=8001,
        debug=True,
        use_reloader=False
    )