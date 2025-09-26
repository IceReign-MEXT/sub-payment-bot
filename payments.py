# payments.py
import os
import requests
from solana.rpc.api import Client

# Environment variables
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

# --- ETH Payment Check via Etherscan ---
def verify_eth_payment(expected_amount):
    """
    Checks if a payment matching expected_amount (ETH) was received.
    Returns True if found, False otherwise.
    """
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": SAFE_ETH_WALLET,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETHERSCAN_KEY
    }
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "1":
            return False

        for tx in data["result"]:
            value_eth = int(tx["value"]) / 10**18
            if abs(value_eth - expected_amount) < 0.000001:
                return True
        return False
    except Exception as e:
        print("ETH payment verification error:", e)
        return False

# --- SOL Payment Check via Solana RPC ---
def verify_sol_payment(expected_amount):
    """
    Checks if a payment matching expected_amount (SOL) was received.
    Returns True if found, False otherwise.
    """
    try:
        client = Client(SOLANA_RPC_URL)
        resp = client.get_balance(SAFE_SOL_WALLET)
        if resp["result"]:
            balance_sol = resp["result"]["value"] / 10**9
            if balance_sol >= expected_amount:
                return True
        return False
    except Exception as e:
        print("SOL payment verification error:", e)
        return False

# --- USD Price Fetching (Optional) ---
def get_crypto_price(symbol: str):
    """
    Fetch price in USD for a given symbol (ETH or SOL) using CoinMarketCap API.
    Returns float USD price, or None if unavailable.
    """
    CMC_API_KEY = os.getenv("CMC_API_KEY")
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": symbol, "convert": "USD"}
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        price = data["data"][symbol]["quote"]["USD"]["price"]
        return price
    except Exception as e:
        print(f"{symbol} price fetch error:", e)
        return None
