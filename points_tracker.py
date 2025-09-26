import logging
import time
from decimal import Decimal
from database import add_points, get_wallet_balance
from manual_handlers import manual_safe_run
from payments import get_latest_transactions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POINTS_PER_USD = 10  # 1 USD = 10 points (you can adjust)

def convert_usd_to_points(usd_amount: float) -> int:
    """Convert USD amount to points."""
    return int(Decimal(usd_amount) * POINTS_PER_USD)

def track_incoming(wallet_address: str, chain: str):
    """Check wallet for new incoming funds and assign points."""
    logger.info(f"Checking {chain} wallet {wallet_address} for new funds...")
    transactions = get_latest_transactions(wallet_address, chain)
    
    if not transactions:
        logger.info("No new transactions found.")
        return

    for tx in transactions:
        usd_value = tx.get("usd_value")
        sender = tx.get("from")
        tx_hash = tx.get("tx_hash")

        points = convert_usd_to_points(usd_value)
        add_points(sender, points, tx_hash=tx_hash)
        logger.info(f"Added {points} points for {sender} from tx {tx_hash}.")

def monitor_wallets():
    """Continuously monitor wallets for incoming funds."""
    while True:
        try:
            manual_safe_run(track_incoming, wallet_address="0x08D171685e51bAf7a929cE8945CF25b3D1Ac9756", chain="ETH")
            manual_safe_run(track_incoming, wallet_address="3JqvK1ZAt67nipBVgZj6zWvuT8icMWBMWyu5AwYnhVss", chain="SOL")
        except Exception as e:
            logger.exception(f"Error monitoring wallets: {e}")
        
        time.sleep(60)  # check every minute

if __name__ == "__main__":
    monitor_wallets()
