#!/usr/bin/env python3
# master_integrity.py
# ICEGODS Master Integrity Orchestrator
# Combines auto-fix, AI integrity checks, wallet monitoring, RPC checks, and notifications

import os
import sys
import time
import logging
import traceback
from datetime import datetime
from threading import Thread

# === Telegram Bot ===
from telegram import Bot
from telegram.error import TelegramError

# === Blockchain / RPC ===
from web3 import Web3
from solana.rpc.api import Client as SolanaClient

# === Local modules ===
try:
    import auto_fix_and_prepare
    import render_health_check
    import audit_and_deploy_check
    import repair_bot_connections
    import render_push_and_redeploy
    import render_auto_restart
except ImportError as e:
    print(f"[ERROR] Module import failed: {e}")
    sys.exit(1)

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# === Environment Variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
ETH_WALLETS = [SAFE_ETH_WALLET, os.getenv("ETH_WALLET")]
SOL_WALLETS = [SAFE_SOL_WALLET, os.getenv("SOL_WALLET")]
BTC_WALLET = os.getenv("BTC_WALLET")

ETH_RPC_URLS = [
    os.getenv("ETH_RPC_URL"),  # Infura
    os.getenv("ALCHEMY_API")  # Alchemy
]

SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")

DATABASE_URL = os.getenv("DATABASE_URL")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

MODE = os.getenv("MODE", "production")

# === Telegram Bot Setup ===
try:
    bot = Bot(token=BOT_TOKEN)
except TelegramError as e:
    logging.error(f"Failed to initialize Telegram bot: {e}")
    bot = None

def notify_admin(message: str):
    if bot and ADMIN_CHAT_ID:
        try:
            bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
            logging.info(f"Sent Telegram notification: {message}")
        except TelegramError as e:
            logging.error(f"Failed to send Telegram notification: {e}")

# === RPC / Wallet Monitoring ===
def check_ethereum():
    for url in ETH_RPC_URLS:
        try:
            w3 = Web3(Web3.HTTPProvider(url))
            if w3.is_connected():
                logging.info(f"Ethereum RPC OK: {url}")
                return w3
        except Exception as e:
            logging.warning(f"Ethereum RPC failed ({url}): {e}")
    notify_admin("⚠️ Ethereum RPC problem: all URLs failed")
    return None

def check_solana():
    try:
        client = SolanaClient(SOLANA_RPC_URL)
        response = client.is_connected()
        if response:
            logging.info(f"Solana RPC OK: {SOLANA_RPC_URL}")
            return client
    except Exception as e:
        logging.warning(f"Solana RPC failed: {e}")
    notify_admin("⚠️ Solana RPC problem")
    return None

def check_wallet_balances(w3: Web3, sol_client: SolanaClient):
    try:
        for eth_wallet in ETH_WALLETS:
            balance = w3.eth.get_balance(eth_wallet)
            logging.info(f"ETH wallet {eth_wallet}: {w3.from_wei(balance, 'ether')} ETH")
        for sol_wallet in SOL_WALLETS:
            balance = sol_client.get_balance(sol_wallet)["result"]["value"]
            logging.info(f"SOL wallet {sol_wallet}: {balance / 1e9} SOL")
    except Exception as e:
        logging.error(f"Wallet balance check failed: {e}")
        notify_admin(f"⚠️ Wallet balance check failed: {e}")

# === AI Integrity & Auto-Fix Loop ===
def run_integrity_checks():
    logging.info("=== Running Master Integrity Checks ===")
    try:
        # Run AI module for integrity checks
        auto_fix_and_prepare.run_checks()
        audit_and_deploy_check.run_audit()
        render_health_check.run_health_check()
        repair_bot_connections.run_repair()
        render_push_and_redeploy.run_push()
        render_auto_restart.run_monitor()
        logging.info("Integrity check completed successfully")
        notify_admin("✅ Master Integrity check completed")
    except Exception as e:
        logging.error(f"Integrity check error: {e}")
        notify_admin(f"⚠️ Integrity check failed: {e}\n{traceback.format_exc()}")

# === Continuous Monitoring ===
def start_monitoring(interval_seconds=60):
    logging.info("Starting continuous monitoring loop...")
    while True:
        try:
            w3 = check_ethereum()
            sol_client = check_solana()
            if w3 and sol_client:
                check_wallet_balances(w3, sol_client)
            run_integrity_checks()
        except Exception as e:
            logging.error(f"Monitoring loop error: {e}")
            notify_admin(f"⚠️ Monitoring loop error: {e}")
        time.sleep(interval_seconds)

# === Main Entry Point ===
if __name__ == "__main__":
    logging.info("ICEGODS Master Integrity starting...")
    notify_admin("🚀 ICEGODS Master Integrity starting...")
    monitoring_thread = Thread(target=start_monitoring, args=(300,), daemon=True)
    monitoring_thread.start()
    monitoring_thread.join()
