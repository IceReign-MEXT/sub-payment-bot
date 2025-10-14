import os
import requests
import time
from datetime import datetime

# === CONFIGURATION ===
# Replace this with your Render app URL (after deploying)
RENDER_APP_URL = "https://your-render-app-name.onrender.com"

# Telegram bot token (to test a basic /help command)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Time between checks (in seconds)
CHECK_INTERVAL = 300  # every 5 minutes

LOG_FILE = "render_health.log"


def log(msg):
    """Write log messages with timestamps."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)


def check_render():
    """Check if the Render web app responds with a healthy status."""
    try:
        response = requests.get(RENDER_APP_URL, timeout=10)
        if response.status_code == 200:
            log("✅ Render app online and responding correctly.")
            return True
        else:
            log(f"⚠️ Render app returned status: {response.status_code}")
            return False
    except Exception as e:
        log(f"❌ Could not reach Render app: {e}")
        return False


def check_bot():
    """Ping Telegram API to confirm bot is alive."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10).json()
        if response.get("ok"):
            log(f"✅ Telegram bot active as @{response['result']['username']}")
            return True
        else:
            log("⚠️ Bot token invalid or bot unreachable.")
            return False
    except Exception as e:
        log(f"❌ Error contacting Telegram: {e}")
        return False


if __name__ == "__main__":
    log("🚀 Starting Render Health Monitor...\n")
    while True:
        render_ok = check_render()
        bot_ok = check_bot()

        if render_ok and bot_ok:
            log("🌐 System stable — all checks passed.\n")
        else:
            log("🚨 Attention required — one or more checks failed.\n")

        time.sleep(CHECK_INTERVAL)
