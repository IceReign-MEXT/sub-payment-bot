#!/usr/bin/env python3
"""
Render Auto Redeploy Script for Sub-Payment-Bot
------------------------------------------------
This script:
  1. Commits & pushes your latest bot code to GitHub
  2. Triggers a rebuild on Render via its REST API
  3. Monitors the build/deploy status
  4. Verifies the health endpoint (if defined)

Usage:
  python3 render_push_and_redeploy.py
"""

import os
import requests
import subprocess
import time
from pathlib import Path

# ---------- USER CONFIG (edit these before running) ----------
REPO_PATH = Path(__file__).resolve().parent
GITHUB_REMOTE = "https://github.com/IceReign-MEXT/sub-payment-bot.git"

# Render API credentials — get from https://render.com/docs/api
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "YOUR_RENDER_API_KEY_HERE")
SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "YOUR_RENDER_SERVICE_ID_HERE")

# Optional health URL (replace with your Render URL)
HEALTH_URL = "https://sub-payment-bot-z1xe.onrender.com/health"

# --------------------------------------------------------------

HEADERS = {"Authorization": f"Bearer {RENDER_API_KEY}"}


def git_push_changes():
    """Commit and push local updates to GitHub"""
    print("📦 Committing and pushing latest changes to GitHub...")
    subprocess.run(["git", "add", "."], cwd=REPO_PATH)
    subprocess.run(["git", "commit", "-m", "🚀 Auto Redeploy Commit"], cwd=REPO_PATH)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=REPO_PATH)
    print("✅ Git push complete.")


def trigger_render_deploy():
    """Trigger a manual deploy via Render API"""
    print("🚀 Triggering redeploy on Render...")
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys"
    r = requests.post(url, headers=HEADERS)
    if r.status_code == 201:
        deploy = r.json()
        deploy_id = deploy["id"]
        print(f"✅ Deploy started. ID: {deploy_id}")
        return deploy_id
    else:
        print("❌ Failed to start deploy:", r.text)
        return None


def wait_for_deploy(deploy_id):
    """Poll Render API until deployment completes"""
    print("⏳ Waiting for deployment to complete...")
    url = f"https://api.render.com/v1/deploys/{deploy_id}"

    for _ in range(60):  # check for ~5 minutes
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("⚠️ Error fetching deploy status:", r.text)
            break
        data = r.json()
        status = data.get("status")
        print(f"   → Status: {status}")
        if status in ["live", "succeeded"]:
            print("✅ Deployment succeeded!")
            return True
        elif status in ["failed", "canceled"]:
            print("❌ Deployment failed.")
            return False
        time.sleep(10)

    print("⚠️ Deployment status timeout.")
    return False


def check_health():
    """Ping the bot's health endpoint"""
    if not HEALTH_URL:
        print("⚠️ No health URL configured.")
        return
    try:
        print(f"🔍 Checking bot health at {HEALTH_URL} ...")
        r = requests.get(HEALTH_URL, timeout=10)
        if r.status_code == 200:
            print("✅ Health check passed.")
        else:
            print(f"⚠️ Health check returned status {r.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")


def main():
    print("🔧 Render Auto Redeploy - Sub-Payment-Bot\n")

    # Sanity check
    if "YOUR_RENDER_API_KEY_HERE" in RENDER_API_KEY:
        print("❌ Please set your RENDER_API_KEY environment variable first!")
        return
    if "YOUR_RENDER_SERVICE_ID_HERE" in SERVICE_ID:
        print("❌ Please set your RENDER_SERVICE_ID environment variable first!")
        return

    git_push_changes()
    deploy_id = trigger_render_deploy()

    if deploy_id:
        ok = wait_for_deploy(deploy_id)
        if ok:
            check_health()
        else:
            print("❌ Deployment failed. Check your Render logs.")
    else:
        print("❌ Unable to start deployment on Render.")


if __name__ == "__main__":
    main()
