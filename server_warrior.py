import os
import time
import logging
from datetime import datetime
from manual_handlers import manual_safe_run
from web3 import Web3
from solana.rpc.api import Client as SolanaClient
from database import get_pending_payment_requests, get_latest_subscription
from payments import get_crypto_price, verify_eth_payment, verify_sol_payment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ServerWarrior")

# Load environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SAFE_ETH_WALLET = os.environ.get("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.environ.get("SAFE_SOL_WALLET")
DATABASE_URL = os.environ.get("DATABASE_URL")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
INFURA_KEY = os.environ.get("INFURA_KEY")
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL")

# Web3 and Solana setup
eth_w3 = Web3(Web3.HTTPProvider(INFURA_KEY)) if INFURA_KEY else None
sol_w3 = SolanaClient(SOLANA_RPC_URL) if SOLANA_RPC_URL else None

# Track last balances to detect new incoming funds
last_eth_balance = None
last_sol_balance = None

def check_env():
    missing = []
    for var in ["BOT_TOKEN", "SAFE_ETH_WALLET", "SAFE_SOL_WALLET", "DATABASE_URL", "CMC_API_KEY", "INFURA_KEY", "SOLANA_RPC_URL"]:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        logger.warning(f"⚠️ Missing environment variables: {', '.join(missing)}")
    else:
        logger.info("✅ All essential environment variables found.")

def check_wallets():
    global last_eth_balance, last_sol_balance

    # Ethereum balance
    try:
        if eth_w3:
            eth_balance = eth_w3.eth.get_balance(SAFE_ETH_WALLET) / 10**18
            if last_eth_balance is not None and eth_balance > last_eth_balance:
                logger.info(f"💰 New ETH funds detected! +{eth_balance - last_eth_balance:.6f} ETH")
            last_eth_balance = eth_balance
            logger.info(f"ETH balance: {eth_balance}")
    except Exception as e:
        logger.warning(f"❌ ETH Wallet check failed: {e}")

    # Solana balance
    try:
        if sol_w3:
            sol_balance = sol_w3.get_balance(SAFE_SOL_WALLET)['result']['value'] / 10**9
            if last_sol_balance is not None and sol_balance > last_sol_balance:
                logger.info(f"💰 New SOL funds detected! +{sol_balance - last_sol_balance:.6f} SOL")
            last_sol_balance = sol_balance
            logger.info(f"SOL balance: {sol_balance}")
    except Exception as e:
        logger.warning(f"❌ SOL Wallet check failed: {e}")

def check_database():
    try:
        subs = get_latest_subscription(0)  # test query
        pending = get_pending_payment_requests()
        logger.info(f"Database OK: subscriptions={subs}, pending={len(pending)}")
    except Exception as e:
        logger.warning(f"❌ Database check failed: {e}")

def monitor_loop(interval=60):
    logger.info("🛡️ Server Warrior started. Monitoring every {} seconds.".format(interval))
    while True:
        manual_safe_run(check_env)
        manual_safe_run(check_database)
        manual_safe_run(check_wallets)
        time.sleep(interval)

if __name__ == "__main__":
    monitor_loop()
