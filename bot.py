import asyncio
from web3 import Web3
from solana.rpc.async_api import AsyncClient as SolanaClient
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Bot
from config import BOT_TOKEN, OWNER_ID, SAFE_ETH_WALLET, SAFE_SOL_WALLET, INFURA_KEY

# Telegram bot instance
bot = Bot(token=BOT_TOKEN)

# Web3 setup (Ethereum)
ETH_RPC = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
w3 = Web3(Web3.HTTPProvider(ETH_RPC))

# Solana setup
solana_client = SolanaClient("https://api.mainnet-beta.solana.com")

# Compromised wallets (add addresses here)
ETH_COMPROMISED_WALLETS = []
SOL_COMPROMISED_WALLETS = []

async def start(update, context):
    await update.message.reply_text("Sub-Payment Bot is online! Monitoring wallets...")

async def check_ethereum_wallets():
    for wallet in ETH_COMPROMISED_WALLETS:
        try:
            balance = await asyncio.to_thread(w3.eth.get_balance, wallet)
            if balance > 0:
                await bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"Ethereum funds detected in {wallet}. Transfer pending."
                )
        except Exception as e:
            await bot.send_message(
                chat_id=OWNER_ID,
                text=f"Error checking Ethereum wallet {wallet}: {str(e)}"
            )

async def check_solana_wallets():
    for wallet in SOL_COMPROMISED_WALLETS:
        try:
            balance_resp = await solana_client.get_balance(wallet)
            if balance_resp["result"]["value"] > 0:
                await bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"Solana funds detected in {wallet}. Transfer pending."
                )
        except Exception as e:
            await bot.send_message(
                chat_id=OWNER_ID,
                text=f"Error checking Solana wallet {wallet}: {str(e)}"
            )

async def wallet_monitoring():
    while True:
        await check_ethereum_wallets()
        await check_solana_wallets()
        await asyncio.sleep(2)  # repeat every 2 seconds

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Start monitoring in the background
    app.create_task(wallet_monitoring())

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())