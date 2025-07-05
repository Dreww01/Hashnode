import schedule
import time
import requests
import os
from datetime import datetime

# Configuration
APP_URL = os.environ.get('APP_URL', 'http://localhost:8000')

def keep_alive():
    """Simple health ping to keep the server awake"""
    try:
        response = requests.get(f"{APP_URL}/health", timeout=10)
        if response.status_code == 200:
            print(f"✓ Server is alive - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"⚠ Server responded with status {response.status_code}")
    except Exception as e:
        print(f"✗ Keep-alive failed: {e}")

# Schedule the keep-alive ping every 5 minutes
schedule.every(5).minutes.do(keep_alive)

print(f"🚀 Keep-alive service started for {APP_URL}")
print("📡 Pinging server every 5 minutes to prevent sleep...")

# Run initial ping
keep_alive()

# Main loop
while True:
    schedule.run_pending()
    time.sleep(1)