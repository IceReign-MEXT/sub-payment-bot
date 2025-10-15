import os
import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from web3 import Web3
import asyncio
import aiohttp
from dotenv import load_dotenv

# === Load environment ===
load_dotenv()

# === Telegram Bot Config ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
MODE = os.getenv("MODE", "testing")

# === Blockchain Config ===
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
ETH_RPC_URL = os.getenv("ETH_RPC_URL")

# === Wallets ===
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
BTC_WALLET = os.getenv("BTC_WALLET")
ETH_WALLET = os.getenv("ETH_WALLET")
SOL_WALLET = os.getenv("SOL_WALLET")

# === Encryption / Security ===
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# === Setup Logging ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# === Ethereum RPC Setup ===
web3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))

# === Solana Setup ===
async def get_solana_balance(wallet_address):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            SOLANA_RPC_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]},
        ) as response:
            data = await response.json()
            balance = data.get("result", {}).get("value", 0) / 1e9
            return balance

# === Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Welcome to ICEGODSDEVILGODS Bot!\n\n"
        f"This bot is connected to:\n"
        f"🔹 Solana: {SOL_WALLET}\n"
        f"🔹 Ethereum: {ETH_WALLET}\n\n"
        f"Type /status to view blockchain wallet stats."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        eth_balance = web3.eth.get_balance(Web3.to_checksum_address(ETH_WALLET))
        eth_in_eth = web3.from_wei(eth_balance, 'ether')
        sol_balance = await get_solana_balance(SOL_WALLET)

        msg = (
            f"💰 **Wallet Status**\n\n"
            f"🔹 Ethereum Wallet: {ETH_WALLET}\n"
            f"   Balance: {eth_in_eth:.6f} ETH\n\n"
            f"🔹 Solana Wallet: {SOL_WALLET}\n"
            f"   Balance: {sol_balance:.6f} SOL\n\n"
            f"⚡ Mode: {MODE}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching balances: {e}")
        logger.error(f"Error in /status: {e}")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Access Denied.")
        return
    await update.message.reply_text(
        f"👑 ICEGODSDEVILGODS ADMIN PANEL 👑\n\n"
        f"🪙 SAFE_ETH_WALLET: {SAFE_ETH_WALLET}\n"
        f"💎 SAFE_SOL_WALLET: {SAFE_SOL_WALLET}\n\n"
        f"⚙️ Current Mode: {MODE}"
    )

# === Deploy Function ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("admin", admin))

    logger.info("🚀 ICEGODSDEVILGODS BOT DEPLOYED SUCCESSFULLY")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("❌ Bot stopped manually.")
