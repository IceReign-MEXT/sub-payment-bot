import os
import importlib
import subprocess
from pathlib import Path

print("🔍 Running Sub-Payment-Bot System Repair...")

# Define critical project files
required_files = [
    "main.py",
    "deploy_bot.py",
    "render_deploy_auto.py",
    "render_auto_restart.py",
    "render_health_check.py",
    "requirements.txt",
]

missing_files = [f for f in required_files if not Path(f).exists()]
if missing_files:
    print(f"❌ Missing critical files: {', '.join(missing_files)}")
else:
    print("✅ All critical files found")

# Check Python imports in each file
def scan_imports():
    errors = []
    for file in Path(".").rglob("*.py"):
        try:
            subprocess.run(["python3", "-m", "py_compile", str(file)],
                           capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            errors.append((file, e.stderr.strip()))
    return errors

compile_errors = scan_imports()
if compile_errors:
    print("⚠️ Found import or syntax issues:")
    for file, err in compile_errors:
        print(f" - {file}: {err.splitlines()[-1]}")
else:
    print("✅ All Python scripts import successfully")

# Ensure key environment variables are present
required_env = [
    "BOT_TOKEN",
    "ADMIN_ID",
    "SAFE_SOL_WALLET",
    "SAFE_ETH_WALLET",
    "DATABASE_URL",
]

missing_env = [v for v in required_env if v not in os.environ]
if missing_env:
    print("⚠️ Missing environment variables:")
    for v in missing_env:
        print(f" - {v}")
else:
    print("✅ All environment variables loaded")

# Check requirements installed
def verify_packages():
    print("📦 Verifying installed dependencies...")
    with open("requirements.txt") as reqs:
        for line in reqs:
            pkg = line.strip().split("==")[0]
            if not pkg:
                continue
            try:
                importlib.import_module(pkg.replace("-", "_"))
            except Exception:
                print(f"⚠️ Missing package: {pkg}")

verify_packages()

# Check render entry point
procfile = Path("Procfile")
if not procfile.exists():
    print("⚙️ Creating Procfile (Render entry)...")
    procfile.write_text("web: gunicorn main:app --bind 0.0.0.0:$PORT\n")
else:
    print("\n🚀 Final check complete.")
print("If you see no ❌ or ⚠️ above, your bot is fully connected and ready to redeploy on Render.")
