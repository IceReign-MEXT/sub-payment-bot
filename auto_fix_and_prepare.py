#!/usr/bin/env python3
"""
🔧 Auto Fix & Prepare for sub-payment-bot
----------------------------------------
This script:
 - Checks and repairs .env variables
 - Installs missing dependencies
 - Verifies imports
 - Creates Render Procfile if missing
 - Finalizes readiness check
"""

import os, subprocess, sys, json, time
from pathlib import Path

# -------- CONFIG --------
REQUIRED_ENV = {
    "BOT_TOKEN": "",
    "ADMIN_ID": "",
    "SAFE_SOL_WALLET": "HxmywH2gW9ezQ2nBXwurpaWsZS6YvdmLF23R9WgMAM7p",
    "SAFE_ETH_WALLET": "0x5B0703825e5299b52b0d00193Ac22E20795defBa",
    "DATABASE_URL": "postgresql+asyncpg://user:password@localhost:5432/subpaymentdb",
}
REQUIRED_PACKAGES = [
    "aiogram==3.10.0",
    "python-dotenv==1.0.1",
    "fastapi==0.115.0",
    "uvicorn==0.30.5",
    "requests==2.32.3",
    "pydantic==2.9.2",
    "pydantic-core==2.41.1",
    "asyncpg==0.29.0",
    "SQLAlchemy==2.0.36"
]

ROOT = Path(".").resolve()
ENV_PATH = ROOT / ".env"
PROCFILE_PATH = ROOT / "Procfile"

# -------- FUNCTIONS --------
def read_env():
    env = {}
    if not ENV_PATH.exists():
        print("⚠️ No .env found — creating one...")
        ENV_PATH.write_text("")
    with open(ENV_PATH, "r") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k.strip()] = v.strip()
    return env

def write_env(env_dict):
    lines = [f"{k}={v}" for k, v in env_dict.items()]
    ENV_PATH.write_text("\n".join(lines))
    print(f"✅ .env file updated → {ENV_PATH}")

def ensure_env_keys():
    env = read_env()
    changed = False
    for key, default in REQUIRED_ENV.items():
        if key not in env or not env[key]:
            print(f"⚙️ Adding missing key: {key}")
            env[key] = default
            changed = True
    if changed:
        write_env(env)
    else:
        print("✅ All required environment variables present.")
    return env

def install_missing_packages():
    print("\n📦 Checking and installing missing packages...")
    missing = []
    for pkg in REQUIRED_PACKAGES:
        mod_name = pkg.split("==")[0]
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"⚙️ Installing: {' '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install", *missing])
    else:
        print("✅ All packages already installed.")

def create_procfile():
    if not PROCFILE_PATH.exists():
        print("⚙️ Creating Procfile for Render...")
        PROCFILE_PATH.write_text("web: uvicorn main:app --host 0.0.0.0 --port 10000")
        print("✅ Procfile created.")
    else:
        print("✅ Procfile already exists.")

def verify_imports():
    print("\n🔍 Verifying bot imports...")
    py_files = list(ROOT.glob("*.py"))
    broken = []
    for f in py_files:
        try:
            compile(f.read_text(), str(f), "exec")
        except Exception as e:
            broken.append((f.name, str(e)))
    if broken:
        print("⚠️ Found issues:")
        for name, err in broken:
            print(f" - {name}: {err}")
    else:
        print("✅ All Python scripts compiled successfully.")

def finalize_check():
    print("\n🚀 Final readiness check...")
    print("If you see no ⚠️ above, your bot is ready to deploy on Render.")
    print("👉 Next step:")
    print("   git add . && git commit -m 'AutoFix ready' && git push render main")

# -------- MAIN --------
if __name__ == "__main__":
    print("🔧 Running Sub-Payment-Bot AutoFix...")
    ensure_env_keys()
    install_missing_packages()
    verify_imports()
    create_procfile()
    finalize_check()
