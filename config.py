import os
from dotenv import load_dotenv

<<<<<<< HEAD
# Load .env file
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin ID (your Telegram numeric ID)
ADMIN_ID = os.getenv("ADMIN_ID", "6453658778")  # default to your ID if not set

# CoinMarketCap API
CMC_API_KEY = os.getenv("CMC_API_KEY")

# Infura / Ethereum
=======
# Load environment variables from .env
load_dotenv()

# --- Telegram Bot Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 12345)) # Replace 12345 with your actual Telegram ID if not set in .env

# --- Blockchain Wallet & API Configuration ---
# Ethereum
>>>>>>> origin/main
INFURA_KEY = os.getenv("INFURA_KEY")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")

# Solana
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
<<<<<<< HEAD
=======

# CoinMarketCap API Key for crypto price fetching
CMC_API_KEY = os.getenv("CMC_API_KEY")

# --- Validate critical configuration ---
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")
if not INFURA_KEY:
    raise ValueError("INFURA_KEY environment variable not set for Ethereum.")
if not SAFE_ETH_WALLET:
    raise ValueError("SAFE_ETH_WALLET environment variable not set.")
if not SAFE_SOL_WALLET:
    raise ValueError("SAFE_SOL_WALLET environment variable not set.")
if not CMC_API_KEY:
    raise ValueError("CMC_API_KEY environment variable not set.")
>>>>>>> origin/main
