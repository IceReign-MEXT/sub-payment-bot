# validate_env.py
import os
from dotenv import load_dotenv
import re

# Load .env file
load_dotenv()

# Required environment variables
required_vars = [
    "BOT_TOKEN",
    "OWNER_ID",
    "OWNER_USERNAME",
    "OWNER_FIRST",
    "OWNER_LAST",
    "OWNER_LANG",
    "SAFE_ETH_WALLET",
    "SAFE_SOL_WALLET",
    "CMC_API_KEY",
    "INFURA_KEY",
    "DATABASE_URL"
]

print("🔍 Checking essential environment variables...")

all_ok = True
for var in required_vars:
    value = os.getenv(var)
    if not value:
        print(f"❌ Missing environment variable: {var}")
        all_ok = False
    else:
        print(f"✅ Found environment variable: {var}")

# Additional sanity checks
eth_wallet = os.getenv("SAFE_ETH_WALLET")
sol_wallet = os.getenv("SAFE_SOL_WALLET")
infura_key = os.getenv("INFURA_KEY")

if eth_wallet and not re.match(r"^0x[a-fA-F0-9]{40}$", eth_wallet):
    print(f"❌ ETH wallet format invalid: {eth_wallet}")
    all_ok = False

if sol_wallet and len(sol_wallet) < 30:  # Solana address is usually >30 chars
    print(f"❌ SOL wallet format seems invalid: {sol_wallet}")
    all_ok = False

if infura_key and not infura_key.startswith("https://"):
    print(f"❌ INFURA_KEY should start with 'https://': {infura_key}")
    all_ok = False

if all_ok:
    print("\n🎉 All environment variables look good! Your bot can run safely.")
else:
    print("\n⚠️ Please fix the issues above before starting the bot.")
