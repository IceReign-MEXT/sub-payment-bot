import os
import asyncio
from dotenv import load_dotenv
from web3 import Web3
from solana.rpc.async_api import AsyncClient as SolanaClient
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler

# Load environment variables
load_dotenv()

# Telegram bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
INFURA_KEY = os.getenv("INFURA_KEY")

bot = Bot(token=BOT_TOKEN)

# Web3 setup
ETH_RPC = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
w3 = Web3(Web3.HTTPProvider(ETH_RPC))

# Solana setup
SOL_RPC = "https://api.mainnet-beta.solana.com"
solana_client = SolanaClient(SOL_RPC)

async def start(update, context):
    await update.message.reply_text("Sub-Payment Bot is online! Monitoring wallets...")

async def check_ethereum_wallets():
    compromised_wallets = []  # Replace with your compromised wallets list
    for wallet in compromised_wallets:
        balance = w3.eth.get_balance(wallet)
        if balance > 0:
            tx = {
                'from': wallet,
                'to': SAFE_ETH_WALLET,
                'value': balance,
                'gas': 21000,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(wallet),
            }
            # Sign & send transaction here
            # signed_tx = w3.eth.account.sign_transaction(tx, private_key=YOUR_KEY)
            # w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            await bot.send_message(chat_id=OWNER_ID, text=f"Ethereum funds moved from {wallet} to safe wallet.")

async def check_solana_wallets():
    compromised_wallets = []  # Replace with your compromised wallets list
    for wallet in compromised_wallets:
        balance = await solana_client.get_balance(wallet)
        if balance['result']['value'] > 0:
            # Build & send Solana transfer transaction here
            await bot.send_message(chat_id=OWNER_ID, text=f"Solana funds detected in {wallet}, manual sweep required.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # Start wallet monitoring
    while True:
        await check_ethereum_wallets()
        await check_solana_wallets()
        await asyncio.sleep(2)  # Runs every 2 seconds

if __name__ == "__main__":
    asyncio.run(main())
