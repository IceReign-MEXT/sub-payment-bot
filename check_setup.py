#!/usr/bin/env python3
import os
import sys
import asyncio
import requests
from dotenv import load_dotenv

print("🔹 Starting full environment check...")

# Load .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(env_path):
    print("❌ .env file not found!")
    sys.exit(1)

load_dotenv(env_path)
print("✅ Loaded .env variables")

# Check essential environment variables
required_env = [
    "BOT_TOKEN", "ADMIN_ID", "ETH_WALLET", "SOL_WALLET",
    "INFURA_URL", "SOLANA_RPC_URL", "DATABASE_URL"
]

for var in required_env:
    if not os.getenv(var):
        print(f"❌ Missing required environment variable: {var}")
    else:
        print(f"✅ {var} is set")

# Test FastAPI endpoints
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
for endpoint in ["/", "/health"]:
    url = BASE_URL.rstrip("/") + endpoint
    try:
        r = requests.get(url, timeout=5)
        print(f"✅ Endpoint {endpoint} responded with status {r.status_code}")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"❌ Failed to reach {endpoint}: {e}")

# Test Telegram Bot token validity
from telegram import Bot
bot_token = os.getenv("BOT_TOKEN")
try:
    bot = Bot(token=bot_token)
    me = bot.get_me()
    print(f"✅ Telegram bot connected as @{me.username}")
except Exception as e:
    print(f"❌ Telegram bot test failed: {e}")

# Test Ethereum RPC
from web3 import Web3
eth_rpc = os.getenv("INFURA_URL")
if eth_rpc:
    try:
        w3 = Web3(Web3.HTTPProvider(eth_rpc))
        if w3.is_connected():
            print(f"✅ Ethereum RPC connected. Latest block: {w3.eth.block_number}")
        else:
            print("❌ Ethereum RPC not responding")
    except Exception as e:
        print(f"❌ Ethereum RPC test failed: {e}")

# Test Solana RPC
try:
    from solana.rpc.async_api import AsyncClient

    async def test_solana():
        async with AsyncClient(os.getenv("SOLANA_RPC_URL")) as client:
            resp = await client.get_epoch_info()
            if resp["result"]:
                print(f"✅ Solana RPC connected. Epoch: {resp['result']['epoch']}")
            else:
                print("❌ Solana RPC response invalid")

    asyncio.run(test_solana())
except Exception as e:
    print(f"❌ Solana RPC test failed: {e}")

print("🔹 Environment check complete!")
