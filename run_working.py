#\!/usr/bin/env python3
"""
Working Flask server - ทำงานได้แน่นอน
"""

from flask import Flask

app = Flask(__name__)
app.secret_key = 'test-secret-key'

@app.route('/')
def home():
    return '''
    <h1>🍽️ LanAim POS System v5.3</h1>
    <h2>✅ เซิร์ฟเวอร์ทำงานได้แล้ว\!</h2>
    <ul>
        <li><a href="/test">Test Page</a></li>
        <li><a href="/health">Health Check</a></li>
        <li><a href="/info">Server Info</a></li>
    </ul>
    <p><strong>Note:</strong> นี่คือเซิร์ฟเวอร์ทดสอบ ยังไม่ใช่ระบบเต็ม</p>
    '''

@app.route('/test')
def test():
    return {'status': 'OK', 'message': 'Test endpoint working\!'}

@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': '2025-07-12'}

@app.route('/info')
def info():
    return {
        'app': 'LanAim POS v5.3',
        'status': 'running',
        'mode': 'test',
        'port': 9000
    }

if __name__ == '__main__':
    print("🚀 Starting working Flask server...")
    print("🔗 Open: http://127.0.0.1:9000")
    print("=" * 40)
    
    app.run(
        host='127.0.0.1',
        port=9000,
        debug=True,
        use_reloader=False
    )
EOF < /dev/null