import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin / Owner ID as integer
OWNER_ID = int(os.getenv("OWNER_ID", 6453658778))  # fallback to your ID if not set

# Ethereum / Infura
INFURA_KEY = os.getenv("INFURA_KEY")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")

# Solana
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")