import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin ID (your Telegram numeric ID)
ADMIN_ID = os.getenv("ADMIN_ID", "6453658778")  # default to your ID if not set

# CoinMarketCap API
CMC_API_KEY = os.getenv("CMC_API_KEY")

# Infura / Ethereum
INFURA_KEY = os.getenv("INFURA_KEY")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")

# Solana
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
