import os
from web3 import Web3
from solana.rpc.api import Client as SolanaClient
from dotenv import load_dotenv

load_dotenv()

SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
INFURA_KEY = os.getenv("INFURA_KEY")

# Ethereum setup
w3 = Web3(Web3.HTTPProvider(INFURA_KEY))

# Solana setup
sol_client = SolanaClient("https://api.mainnet-beta.solana.com")

# Subscription plans
PLANS = {
    "Daily": {"price": 5, "duration": 1},
    "Weekly": {"price": 20, "duration": 7},
    "Monthly": {"price": 50, "duration": 30},
    "Yearly": {"price": 500, "duration": 365},
    "Lifetime": {"price": 1000, "duration": None},
}

# Handle subscription selection
def handle_subscription(update, context, plan):
    """Save selected plan in user_data"""
    context.user_data["selected_plan"] = plan

# Verify ETH payment (user-to-safe wallet)
def verify_eth_payment(tx_hash: str, amount_eth: float):
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if tx.to.lower() == SAFE_ETH_WALLET.lower():
            value_eth = w3.from_wei(tx.value, "ether")
            return value_eth >= amount_eth
    except Exception as e:
        print("❌ ETH verify error:", e)
    return False

# Verify SOL payment (user-to-safe wallet)
def verify_sol_payment(signature: str, amount_sol: float):
    try:
        tx_resp = sol_client.get_confirmed_transaction(signature)
        if tx_resp["result"]:
            tx = tx_resp["result"]["transaction"]
            for instr in tx["message"]["instructions"]:
                if instr.get("parsed") and instr["parsed"]["info"]["destination"] == SAFE_SOL_WALLET:
                    lamports = int(instr["parsed"]["info"]["lamports"])
                    sol_value = lamports / 10**9
                    return sol_value >= amount_sol
    except Exception as e:
        print("❌ SOL verify error:", e)
    return False
