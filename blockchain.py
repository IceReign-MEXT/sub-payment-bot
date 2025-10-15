# blockchain.py
import os, asyncio
from web3 import Web3
from solana.rpc.async_api import AsyncClient
from dotenv import load_dotenv
load_dotenv()

INFURA_URL = os.getenv("INFURA_URL")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
ETH_CONFIRMATIONS = int(os.getenv("ETH_CONFIRMATIONS", "3"))
SOL_CONFIRMATIONS = int(os.getenv("SOL_CONFIRMATIONS", "1"))

w3 = Web3(Web3.HTTPProvider(INFURA_URL)) if INFURA_URL else None

async def sol_get_balance(addr):
    async with AsyncClient(SOLANA_RPC_URL) as client:
        res = await client.get_balance(addr)
        # returns lamports; convert to SOL
        if "result" in res and res["result"]:
            lamports = res["result"]["value"]
            return lamports / 1e9
        return None

def eth_get_tx(tx_hash):
    if not w3:
        return None
    try:
        tx = w3.eth.get_transaction(tx_hash)
        return tx
    except Exception:
        return None

def eth_get_confirmations(tx_hash):
    if not w3: return 0
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if not tx or not tx.blockNumber:
            return 0
        return w3.eth.block_number - tx.blockNumber
    except Exception:
        return 0

# helper: check if tx is confirmed enough
def eth_is_confirmed(tx_hash, required=3):
    confs = eth_get_confirmations(tx_hash)
    return confs >= required
