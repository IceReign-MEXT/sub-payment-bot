import os
import subprocess
from dotenv import load_dotenv

print("🚀 Preparing Auto Deployment for Render...")

# Load environment variables
load_dotenv()

# 1️⃣ Check for main.py
if not os.path.exists("main.py"):
    print("❌ main.py not found. Make sure it’s in your project folder.")
    exit()

# 2️⃣ Check requirements
if not os.path.exists("requirements.txt"):
    print("❌ requirements.txt not found.")
    exit()

# 3️⃣ Install dependencies
print("📦 Installing dependencies...")
subprocess.run(["pip", "install", "-r", "requirements.txt"])

# 4️⃣ Check critical environment variables
required_envs = ["BOT_TOKEN", "SAFE_ETH_WALLET", "SAFE_SOL_WALLET"]
missing_envs = [e for e in required_envs if not os.getenv(e)]

if missing_envs:
    print("⚠️ Missing required env variables:")
    for e in missing_envs:
        print(f"  - {e}")
else:
    print("✅ Environment variables loaded successfully.")

# 5️⃣ Create Render build structure
os.makedirs("render_build", exist_ok=True)

# Copy main files
for file in ["main.py", "requirements.txt", ".env"]:
    if os.path.exists(file):
        subprocess.run(["cp", file, "render_build/"])

# 6️⃣ Generate render.yaml
render_yaml = """services:
  - type: worker
    name: ice-sub-bot
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python main.py"
    autoDeploy: true
"""

with open("render_build/render.yaml", "w") as f:
    f.write(render_yaml)

print("✅ Render configuration generated (render_build/render.yaml)")

# 7️⃣ Zip the folder for upload
print("🧩 Creating deployment bundle...")
subprocess.run(["zip", "-r", "render_deploy.zip", "render_build"])

print("\n🎉 Done! You can now upload 'render_deploy.zip' to Render:")
print("👉 Go to https://render.com, create a new Web Service, and upload the zip.")
print("Render will detect the Python app and start your bot automatically.")
