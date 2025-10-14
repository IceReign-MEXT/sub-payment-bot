import os
import requests
import time
from datetime import datetime

# === CONFIGURATION ===
# Get from your Render dashboard (Account → API Keys)
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "YOUR_RENDER_API_KEY_HERE")

# The ID of your Render service (find this on the Render dashboard)
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "YOUR_RENDER_SERVICE_ID_HERE")

# How often to check (seconds)
CHECK_INTERVAL = 600  # 10 minutes

# URL of your deployed app (used for ping check)
RENDER_APP_URL = os.getenv("RENDER_APP_URL", "https://your-render-app.onrender.com")

# Log file
LOG_FILE = "auto_restart.log"


def log(msg):
    """Log with timestamp."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")


def restart_render_service():
    """Trigger a restart for the Render service."""
    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {"clearCache": True}
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            log("♻️ Restart triggered successfully on Render.")
        else:
            log(f"⚠️ Failed to trigger restart: {response.status_code} {response.text}")
    except Exception as e:
        log(f"❌ Error contacting Render API: {e}")


def check_service():
    """Ping the Render web app."""
    try:
        res = requests.get(RENDER_APP_URL, timeout=10)
        if res.status_code == 200:
            log("✅ Render app responding correctly.")
            return True
        else:
            log(f"⚠️ Render returned {res.status_code}")
            return False
    except Exception as e:
        log(f"❌ App not responding: {e}")
        return False


if __name__ == "__main__":
    log("🚀 Starting Render Auto-Restart Service...\n")

    while True:
        if not check_service():
            log("🚨 Service appears down. Initiating auto-restart sequence...")
            restart_render_service()
            log("⏳ Waiting before next check...\n")
            time.sleep(180)  # wait 3 minutes before next check
        else:
            log("🌐 All systems operational.\n")

        time.sleep(CHECK_INTERVAL)
