#!/usr/bin/env python3
"""
Test script for feedback analytics page
"""

from app_production import create_production_app
import threading
import time
import requests

def run_app():
    app = create_production_app()
    app.run(host='127.0.0.1', port=5002, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Start the app in a separate thread
    app_thread = threading.Thread(target=run_app, daemon=True)
    app_thread.start()
    
    # Wait for the app to start
    time.sleep(3)
    
    # Test the feedback page
    try:
        response = requests.get('http://127.0.0.1:5002/admin/analytics/feedback', timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 302:
            print("Redirected to login (expected for unauthenticated request)")
            print(f"Redirect Location: {response.headers.get('Location', 'No location')}")
        elif response.status_code == 500:
            print("Internal Server Error - checking content...")
            print(response.text[:1000])
        elif response.status_code == 200:
            print("Success! Page loaded correctly")
            print(f"Content length: {len(response.text)} characters")
        else:
            print(f"Unexpected status code: {response.status_code}")
            print(response.text[:500])
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Error: {e}")