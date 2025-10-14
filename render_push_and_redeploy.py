#!/usr/bin/env python3
"""
Render Auto Redeploy Script for Sub-Payment-Bot
------------------------------------------------
1. Pushes latest code to GitHub
2. Triggers redeploy on Render
3. Waits for completion
4. Verifies health endpoint
"""

import subprocess
import requests
import time
from pathlib import Path

# ---------- CONFIG ----------
REPO_PATH = Path(__file__).resolve().parent
GITHUB_REMOTE = "https://github.com/IceReign-MEXT/sub-payment-bot.git"

# Replace these two with your actual values
RENDER_API_KEY = "your_real_render_api_key"
SERVICE_ID = "srv-yourrealserviceid"

# Optional: your deployed service health URL
HEALTH_URL = "https://sub-payment-bot-z1xe.onrender.com/health"

HEADERS = {"Authorization": f"Bearer {RENDER_API_KEY}"}

# ---------- FUNCTIONS ----------
def git_push_changes():
    print("📦 Committing and pushing latest changes to GitHub...")
    subprocess.run(["git", "add", "."], cwd=REPO_PATH)
    subprocess.run(["git", "commit", "-m", "🚀 Auto Redeploy Commit"], cwd=REPO_PATH)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=REPO_PATH)
    print("✅ Git push complete.")

def trigger_render_deploy():
    print("🚀 Triggering deploy on Render...")
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys"
    r = requests.post(url, headers=HEADERS)
    if r.status_code == 201:
        deploy_id = r.json().get("id")
        print(f"✅ Deploy started. ID: {deploy_id}")
        return deploy_id
    print(f"❌ Failed to start deploy ({r.status_code}): {r.text}")
    return None

def wait_for_deploy(deploy_id):
    print("⏳ Waiting for deployment to complete...")
    url = f"https://api.render.com/v1/deploys/{deploy_id}"
    for _ in range(60):
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("⚠️ Error fetching deploy status:", r.text)
            break
        data = r.json()
        status = data.get("status")
        print(f"   → Status: {status}")
        if status in ("live", "succeeded"):
            print("✅ Deployment succeeded!")
            return True
        if status in ("failed", "canceled"):
            print("❌ Deployment failed.")
            return False
        time.sleep(10)
    print("⚠️ Deployment timeout.")
    return False

def check_health():
    if not HEALTH_URL:
        print("⚠️ No health URL configured.")
        return
    try:
        print(f"🔍 Checking health at {HEALTH_URL} ...")
        r = requests.get(HEALTH_URL, timeout=10)
        print("✅ Health check passed." if r.status_code == 200 else f"⚠️ Health returned {r.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

def main():
    print("🔧 Render Auto Redeploy - Sub-Payment-Bot\n")
    git_push_changes()
    deploy_id = trigger_render_deploy()
    if deploy_id:
        if wait_for_deploy(deploy_id):
            check_health()
        else:
            print("❌ Deployment failed. Check Render logs.")
    else:
        print("❌ Unable to start deployment on Render.")

if __name__ == "__main__":
    main()
