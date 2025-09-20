from web3 import Web3
from solana.rpc.api import Client as SolanaClient
from config import SAFE_ETH_WALLET, SAFE_SOL_WALLET, INFURA_KEY

# Ethereum setup
w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))

# Solana setup
sol_client = SolanaClient("https://api.mainnet-beta.solana.com")

def verify_eth_payment(tx_hash: str, amount_eth: float) -> bool:
    """Check if a given ETH transaction to SAFE_ETH_WALLET is valid"""
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if tx.to and tx.to.lower() == SAFE_ETH_WALLET.lower():
            value_eth = w3.from_wei(tx.value, "ether")
            return value_eth >= amount_eth
    except Exception as e:
        print("❌ ETH verify error:", e)
    return False

def verify_sol_payment(signature: str, amount_sol: float) -> bool:
    """Check if a given SOL transaction to SAFE_SOL_WALLET is valid"""
    try:
        tx_resp = sol_client.get_confirmed_transaction(signature)
        if tx_resp.get("result"):
            tx = tx_resp["result"]["transaction"]
            for instr in tx["message"]["instructions"]:
                parsed = instr.get("parsed")
                if parsed and parsed["info"]["destination"] == SAFE_SOL_WALLET:
                    lamports = int(parsed["info"]["lamports"])
                    sol_value = lamports / 10**9
                    return sol_value >= amount_sol
    except Exception as e:
        print("❌ SOL verify error:", e)
    return False