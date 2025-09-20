import os
import requests
from web3 import Web3
from solana.rpc.async_api import AsyncClient as SolanaClient
from config import SAFE_ETH_WALLET, SAFE_SOL_WALLET, INFURA_KEY, CMC_API_KEY
from solders.pubkey import Pubkey
from decimal import Decimal, getcontext

# Set precision for Decimal calculations
getcontext().prec = 10

# --- Blockchain Client Setup ---
# Ethereum setup
w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))

# Solana setup
sol_client = SolanaClient("https://api.mainnet-beta.solana.com")

# --- Crypto Price Fetching ---
def get_crypto_price(symbol: str) -> float | None:
    """Fetches the current USD price of a cryptocurrency from CoinMarketCap."""
    try:
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        params = {"symbol": symbol.upper(), "convert": "USD"}
        resp = requests.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest", headers=headers, params=params, timeout=5)
        resp.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = resp.json()
        return float(data["data"][symbol.upper()]["quote"]["USD"]["price"])
    except requests.exceptions.RequestException as req_err:
        print(f"❌ CMC API request error for {symbol}: {req_err}")
    except KeyError:
        print(f"❌ CMC API response error: Symbol {symbol} not found or data structure changed.")
    except Exception as e:
        print(f"❌ get_crypto_price error for {symbol}: {e}")
    return None

# --- Blockchain Verification Functions ---
async def verify_eth_payment(tx_hash: str, expected_amount_eth: float) -> bool:
    """
    Check if a given ETH transaction to SAFE_ETH_WALLET is valid.
    Checks: transaction existence, recipient address, and amount sent.
    """
    try:
        # Get transaction details
        tx = w3.eth.get_transaction(tx_hash)
        if not tx:
            print(f"❌ ETH Transaction {tx_hash} not found.")
            return False

        # Check destination address
        if tx.to and tx.to.lower() != SAFE_ETH_WALLET.lower():
            print(f"❌ ETH Transaction {tx_hash}: Incorrect recipient address.")
            return False

        # Check transaction value
        value_wei = tx.value
        value_eth = Decimal(w3.from_wei(value_wei, "ether"))
        
        # Allow a small tolerance for floating point comparisons if necessary, but direct comparison is usually fine here
        if value_eth >= Decimal(expected_amount_eth):
            return True
        else:
            print(f"❌ ETH Transaction {tx_hash}: Amount mismatch. Sent: {value_eth} ETH, Expected: {expected_amount_eth} ETH.")
            return False

    except Exception as e:
        print(f"❌ ETH verify error for tx {tx_hash}: {e}")
    return False

async def verify_sol_payment(signature: str, expected_amount_sol: float) -> bool:
    """
    Check if a given SOL transaction (identified by its signature) to SAFE_SOL_WALLET is valid.
    Checks: transaction existence, recipient address, and amount sent.
    """
    try:
        # Get confirmed transaction details
        tx_resp = await sol_client.get_confirmed_transaction(signature, commitment="confirmed")
        
        if not tx_resp or not tx_resp.value:
            print(f"❌ SOL Transaction {signature} not found or not confirmed.")
            return False

        # Transaction details are nested under tx_resp.value.transaction
        tx = tx_resp.value.transaction

        # Check for transfer instruction and recipient
        destination_pubkey = Pubkey.from_string(SAFE_SOL_WALLET)
        
        # Iterate through instructions to find the relevant transfer
        # This parsing might need adjustments based on the exact transaction type (e.g., system program transfer, token transfer)
        is_transfer_to_safe_wallet = False
        total_transfer_to_safe_wallet = Decimal(0)

        # For simple system program transfers
        if tx.message.instructions:
            for instr in tx.message.instructions:
                # The 'parsed' field for system instructions reveals transfer details
                if hasattr(instr, 'parsed') and instr.parsed:
                    if instr.parsed.get('type') == 'transfer' and \
                       instr.parsed['info'].get('destination') == str(destination_pubkey):
                        lamports = Decimal(instr.parsed['info'].get('lamports', 0))
                        total_transfer_to_safe_wallet += lamports
                        is_transfer_to_safe_wallet = True

        if not is_transfer_to_safe_wallet:
            print(f"❌ SOL Transaction {signature}: No transfer instruction found to {SAFE_SOL_WALLET}.")
            return False

        sol_value = total_transfer_to_safe_wallet / Decimal(10**9) # Lamports to SOL conversion

        if sol_value >= Decimal(expected_amount_sol):
            return True
        else:
            print(f"❌ SOL Transaction {signature}: Amount mismatch. Sent: {sol_value} SOL, Expected: {expected_amount_sol} SOL.")
            return False

    except Exception as e:
        print(f"❌ SOL verify error for signature {signature}: {e}")
    return False

