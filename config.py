import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SAFE_ETH_WALLET = os.environ.get("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.environ.get("SAFE_SOL_WALLET")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
