import os
import logging
import sqlite3
import psycopg2
import time
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Function to check database tables and basic data
def check_database():
    print("\n🗄️ Checking database tables and essential entries...")
    try:
        if DATABASE_URL.startswith("sqlite"):
            conn = sqlite3.connect(DATABASE_URL.split("///")[1])
        else:  # PostgreSQL
            conn = psycopg2.connect(DATABASE_URL)
        c = conn.cursor()

        # Check subscriptions table
        try:
            c.execute("SELECT COUNT(*) FROM subscriptions;")
            subs_count = c.fetchone()[0]
            print(f"✅ 'subscriptions' table exists, {subs_count} records found")
        except:
            print("❌ 'subscriptions' table missing or cannot be read")

        # Check pending_payments table
        try:
            c.execute("SELECT COUNT(*) FROM pending_payments;")
            pending_count = c.fetchone()[0]
            print(f"✅ 'pending_payments' table exists, {pending_count} records found")
        except:
            print("❌ 'pending_payments' table missing or cannot be read")

        # Optionally: check if SAFE wallets are used in pending payments
        c.execute("SELECT DISTINCT chain FROM pending_payments;")
        chains = [row[0] for row in c.fetchall()]
        if chains:
            print(f"🔹 Pending payments chains found: {chains}")
        else:
            print("🔹 No pending payments found yet")

        conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

# Function to simulate payment verification
def check_wallets():
    print("\n💰 Checking Ethereum and Solana wallet balances...")
    try:
        from web3 import Web3
        from solana.rpc.api import Client as SolanaClient

        eth_wallet = os.getenv("SAFE_ETH_WALLET")
        sol_wallet = os.getenv("SAFE_SOL_WALLET")
        infura_key = os.getenv("INFURA_KEY")

        if eth_wallet and infura_key:
            w3 = Web3(Web3.HTTPProvider(infura_key))
            eth_balance = w3.eth.get_balance(eth_wallet)
            print(f"✅ Ethereum wallet balance: {w3.from_wei(eth_balance,'ether')} ETH")

        if sol_wallet:
            sol_client = SolanaClient("https://api.mainnet-beta.solana.com")
            sol_resp = sol_client.get_balance(sol_wallet)
            sol_balance = sol_resp['result']['value'] / 1e9
            print(f"✅ Solana wallet balance: {sol_balance} SOL")

    except Exception as e:
        print(f"❌ Wallet balance check failed: {e}")

# Function to check essential environment variables
def check_env_vars():
    print("\n🌐 Checking essential environment variables...")
    ENV_VARS = [
        "BOT_TOKEN", "OWNER_ID", "OWNER_USERNAME", "OWNER_FIRST",
        "OWNER_LAST", "SAFE_ETH_WALLET", "SAFE_SOL_WALLET",
        "CMC_API_KEY", "INFURA_KEY", "DATABASE_URL"
    ]
    missing = False
    for var in ENV_VARS:
        if not os.getenv(var):
            print(f"❌ Missing environment variable: {var}")
            missing = True
        else:
            print(f"✅ Found environment variable: {var}")
    if missing:
        print("⚠️ Some environment variables are missing. Please fix before deployment.")

# Main execution
if __name__ == "__main__":
    check_env_vars()
    check_database()
    check_wallets()
    print("\n🎉 Validation complete! Your bot is ready for deployment if all checks passed.")
