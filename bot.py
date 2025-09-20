# bot.py
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
from web3 import Web3
from solana.rpc.api import Client as SolanaClient

# Load environment variables
load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

# Web3 / Ethereum setup
INFURA_KEY = os.getenv("INFURA_KEY")
ETH_RPC = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
w3 = Web3(Web3.HTTPProvider(ETH_RPC))

# Solana setup
SOL_RPC = "https://api.mainnet-beta.solana.com"
sol_client = SolanaClient(SOL_RPC)

# Example safe wallets (from your environment)
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")

# Bot command examples
async def start(update, context):
    await update.message.reply_text("Hello! I am your Sub-Payment Bot.")

async def ping(update, context):
    await update.message.reply_text("Pong!")

# Create bot application
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Add handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))

# Start bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
