import asyncio
from web3 import Web3
from solana.rpc.async_api import AsyncClient as SolanaClient
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Bot
from config import BOT_TOKEN, OWNER_ID, SAFE_ETH_WALLET, SAFE_SOL_WALLET, INFURA_KEY

# Telegram bot
bot = Bot(token=BOT_TOKEN)

# Web3 setup (Ethereum)
ETH_RPC = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
w3 = Web3(Web3.HTTPProvider(ETH_RPC))

# Solana setup
SOL_RPC = "https://api.mainnet-beta.solana.com"
solana_client = SolanaClient(SOL_RPC)

# Add your compromised wallets here
ETH_COMPROMISED_WALLETS = []
SOL_COMPROMISED_WALLETS = []

async def start(update, context):
    await update.message.reply_text("Sub-Payment Bot is online! Monitoring wallets...")

async def check_ethereum_wallets():
    for wallet in ETH_COMPROMISED_WALLETS:
        try:
            balance = w3.eth.get_balance(wallet)
            if balance > 0:
                tx = {
                    "from": wallet,
                    "to": SAFE_ETH_WALLET,
                    "value": balance,
                    "gas": 21000,
                    "gasPrice": w3.eth.gas_price,
                    "nonce": w3.eth.get_transaction_count(wallet),
                }
                # TODO: Sign & send transaction with private key securely
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
                # TODO: Sign & send Solana transaction securely
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
        await asyncio.sleep(2)  # runs every 2 seconds

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Start wallet monitoring alongside Telegram bot
    asyncio.create_task(wallet_monitoring())

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())