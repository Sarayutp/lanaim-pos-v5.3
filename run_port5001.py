#!/usr/bin/env python3
"""
Run the application on port 5001
"""

from app_production import create_production_app

if __name__ == '__main__':
    app = create_production_app()
    print("Starting application on http://127.0.0.1:5001")
    print("Analytics feedback page: http://127.0.0.1:5001/admin/analytics/feedback")
    app.run(host='127.0.0.1', port=5001, debug=True)