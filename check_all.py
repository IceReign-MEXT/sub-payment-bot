#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()
import os
import sys
import importlib.util
import subprocess

print("=== Quick Pre-Deployment Integrity Check ===\n")

# 1️⃣ Check critical scripts
scripts = [
    "deploy_bot.py",
    "main.py",
    "master_integrity.py",
    "integrity_master.py",
    "test_connections.py",
    "start_all.sh",
    "setup_env.sh"
]

print("Checking critical scripts:")
for s in scripts:
    exists = "✅" if os.path.isfile(s) else "❌ MISSING"
    print(f"{s}: {exists}")

# 2️⃣ Check .env variables
env_vars = [
    "BOT_TOKEN",
    "ADMIN_ID",
    "ADMIN_CHAT_ID",
    "SAFE_SOL_WALLET",
    "SAFE_ETH_WALLET",
    "SOL_WALLET",
    "ETH_WALLET",
    "ETH_RPC_URL",
    "SOLANA_RPC_URL",
    "DATABASE_URL",
    "ENCRYPTION_KEY",
    "MODE"
]

print("\nChecking .env variables:")
env_path = ".env"
if not os.path.isfile(env_path):
    print("❌ .env file missing!")
else:
    with open(env_path) as f:
        content = f.read()
    for var in env_vars:
        if var in content:
            print(f"{var}: ✅ OK")
        else:
            print(f"{var}: ❌ MISSING")

# 3️⃣ Check Python packages
print("\nChecking required Python packages:")
req_file = "requirements.txt"
if not os.path.isfile(req_file):
    print("❌ requirements.txt missing!")
else:
    with open(req_file) as f:
        packages = [line.strip().split("==")[0] for line in f if line.strip() and not line.startswith("#")]
    for pkg in packages:
        if importlib.util.find_spec(pkg):
            print(f"{pkg}: ✅ Installed")
        else:
            print(f"{pkg}: ❌ Not installed")

# 4️⃣ Check Ethereum + Solana RPCs
print("\nChecking RPC endpoints:")
try:
    from web3 import Web3
    eth_url = os.getenv("ETH_RPC_URL")
    if not eth_url:
        print("ETH_RPC_URL not set")
    else:
        w3 = Web3(Web3.HTTPProvider(eth_url))
        print(f"Ethereum RPC: {'✅ OK' if w3.is_connected() else '❌ FAILED'}")
except Exception as e:
    print(f"Ethereum RPC: ❌ ERROR ({e})")

try:
    import requests
    sol_url = os.getenv("SOLANA_RPC_URL")
    if not sol_url:
        print("SOLANA_RPC_URL not set")
    else:
        r = requests.post(sol_url, json={"jsonrpc":"2.0","id":1,"method":"getHealth"})
        if r.ok and r.json().get("result")=="ok":
            print("Solana RPC: ✅ OK")
        else:
            print("Solana RPC: ❌ FAILED")
except Exception as e:
    print(f"Solana RPC: ❌ ERROR ({e})")

# 5️⃣ Check Telegram bot
print("\nChecking Telegram bot connection:")
import telegram
bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    print("BOT_TOKEN not set ❌")
else:
    try:
        bot = telegram.Bot(token=bot_token)
        bot.get_me()
        print(f"Telegram Bot: ✅ OK")
    except Exception as e:
        print(f"Telegram Bot: ❌ FAILED ({e})")

print("\n=== Pre-Deployment Check Complete ===")
