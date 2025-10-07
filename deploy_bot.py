import os
import psycopg2
from dotenv import load_dotenv
from web3 import Web3
import asyncio
from solana.rpc.async_api import AsyncClient

load_dotenv()

SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
INFURA_KEY = os.getenv("INFURA_KEY")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
DATABASE_URL = os.getenv("DATABASE_URL")

async def check_solana():
    print("🔹 Checking Solana RPC...")
    async with AsyncClient(SOLANA_RPC_URL) as client:
        res = await client.get_balance(SAFE_SOL_WALLET)
        if "result" in res:
            print(f"✅ SOL balance for {SAFE_SOL_WALLET}: {res['result']['value']} lamports")
        else:
            print(f"❌ Solana fetch failed: {res}")

def check_ethereum():
    print("🔹 Checking Ethereum RPC...")
    w3 = Web3(Web3.HTTPProvider(INFURA_KEY))
    if w3.is_connected():
        bal = w3.eth.get_balance(SAFE_ETH_WALLET)
        print(f"✅ ETH balance for {SAFE_ETH_WALLET}: {w3.from_wei(bal, 'ether')} ETH")
    else:
        print("❌ Ethereum RPC failed")

def check_database():
    print("🔹 Checking database connection...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        print("✅ Database OK")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database failed: {e}")

async def main():
    print("[INFO] Validating environment and connections...")
    check_database()
    check_ethereum()
    await check_solana()
    print("[OK] All systems initialized.")

if __name__ == "__main__":
    asyncio.run(main())
