<<<<<<< HEAD
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

# Verify ETH payment
def verify_eth_payment(user_wallet, amount_eth):
    balance = w3.eth.get_balance(SAFE_ETH_WALLET)
    balance_eth = w3.from_wei(balance, "ether")
    return balance_eth >= amount_eth

# Verify SOL payment
def verify_sol_payment(user_wallet, amount_sol):
    resp = sol_client.get_balance(SAFE_SOL_WALLET)
    balance_lamports = resp["result"]["value"]
    balance_sol = balance_lamports / 10**9
    return balance_sol >= amount_sol
=======
# Subscription plans with price (USD) and duration (days)
PLANS = {
    "Daily": {"price": 5, "duration": 1},
    "Weekly": {"price": 20, "duration": 7},
    "Monthly": {"price": 50, "duration": 30},
    "Yearly": {"price": 500, "duration": 365},
    "Lifetime": {"price": 1000, "duration": None}, # Use None for lifetime, handled in duration calculation
}

# You can add more subscription-related logic here if needed
# For example, checking if a user has an active subscription etc.

>>>>>>> origin/main
