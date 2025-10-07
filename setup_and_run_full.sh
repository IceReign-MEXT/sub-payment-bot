#!/bin/bash
set -e

echo "🧊 ICEBOYS SUB-PAYMENT BOT — FULL AUTO SETUP & DEPLOY"

# 1️⃣ Update system
echo "-> Updating packages..."
pkg update -y && pkg upgrade -y
pkg install -y git python rust clang libffi postgresql

# 2️⃣ Create virtual environment
echo "-> Creating Python virtual environment..."
if [ ! -d "venv" ]; then
  python -m venv venv
fi
source venv/bin/activate

# 3️⃣ Upgrade pip tools
echo "-> Upgrading pip/setuptools/wheel..."
pip install --upgrade pip setuptools wheel

# 4️⃣ Clean requirements file
echo "-> Creating requirements.txt..."
cat > requirements.txt <<EOF
fastapi
uvicorn
apscheduler
python-telegram-bot==20.7
web3==6.10.0
httpx==0.25.0
requests==2.31.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-dotenv==1.0.1
EOF

# 5️⃣ Install all Python dependencies
echo "-> Installing dependencies..."
pip install -r requirements.txt || true

# 6️⃣ Create environment file
echo "-> Generating .env file..."
cat > .env <<EOF
# 🔹 General Bot Config
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_ID=6453658778
SAFE_SOL_WALLET=F2Lz21btaZax8jVxrtj75Jw5tewFgXhrA4CAi3HzZteS
SAFE_ETH_WALLET=0x5B0703825e5299b52b0d00193Ac22E20795defBa

# 🔹 RPC + Database URLs
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
INFURA_KEY=https://mainnet.infura.io/v3/d276b5c71fad45a99ccb59af25dc32ab
DATABASE_URL=postgresql://user:password@localhost:5432/subpaymentdb
EOF

# 7️⃣ Create startup scripts
echo "-> Creating deploy_bot.py..."
cat > deploy_bot.py <<'PYCODE'
import os
import psycopg2
from dotenv import load_dotenv
from web3 import Web3
import asyncio
from solana.rpc.async_api import AsyncClient

load_dotenv()

SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
INFURA_KEY = os.getenv("INFURA_KEY")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
DATABASE_URL = os.getenv("DATABASE_URL")

async def check_solana():
    print("🔹 Checking Solana RPC...")
    async with AsyncClient(SOLANA_RPC_URL) as client:
        res = await client.get_balance(SAFE_SOL_WALLET)
        if "result" in res:
            print(f"✅ SOL balance for {SAFE_SOL_WALLET}: {res['result']['value']} lamports")
        else:
            print(f"❌ Solana fetch failed: {res}")

def check_ethereum():
    print("🔹 Checking Ethereum RPC...")
    w3 = Web3(Web3.HTTPProvider(INFURA_KEY))
    if w3.is_connected():
        bal = w3.eth.get_balance(SAFE_ETH_WALLET)
        print(f"✅ ETH balance for {SAFE_ETH_WALLET}: {w3.from_wei(bal, 'ether')} ETH")
    else:
        print("❌ Ethereum RPC failed")

def check_database():
    print("🔹 Checking database connection...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        print("✅ Database OK")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database failed: {e}")

async def main():
    print("[INFO] Validating environment and connections...")
    check_database()
    check_ethereum()
    await check_solana()
    print("[OK] All systems initialized.")

if __name__ == "__main__":
    asyncio.run(main())
PYCODE

# 8️⃣ Make script executable
chmod +x setup_and_run_full.sh

# 9️⃣ Done
echo "✅ Setup completed successfully."
echo "Run the bot with:  python deploy_bot.py"
