import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin / Owner ID
OWNER_ID = os.getenv("OWNER_ID")

# Ethereum / Infura
INFURA_KEY = os.getenv("INFURA_KEY")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")

# Solana
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
