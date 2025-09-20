import requests
from telegram import Update
from telegram.ext import ContextTypes

# Example receiving wallets (replace with your safe wallets)
RECEIVING_WALLETS = {
    "ETH": "0xF2776435A6ba8dEaA6F90546B13B8a0E3eB751DD",
    "SOL": "Cqnz6K1BeP7PUXxPtMJeXE3k7BKDYExh49g3aR19nva8"
}

# CoinMarketCap API (replace with your own API key later)
CMC_API_KEY = "YOUR_CMC_API_KEY"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

def get_crypto_price(symbol: str):
    """Fetch current crypto price in USD from CoinMarketCap"""
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": symbol, "convert": "USD"}

    try:
        response = requests.get(CMC_URL, headers=headers, params=params)
        data = response.json()
        return float(data["data"][symbol]["quote"]["USD"]["price"])
    except Exception as e:
        print("❌ Price fetch error:", e)
        return None

async def request_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str, price_usd: float):
    """Ask user to pay in ETH or SOL"""
    eth_price = get_crypto_price("ETH")
    sol_price = get_crypto_price("SOL")

    if not eth_price or not sol_price:
        await update.callback_query.message.reply_text("❌ Failed to fetch crypto prices. Try again later.")
        return

    # Calculate amounts
    eth_amount = round(price_usd / eth_price, 6)
    sol_amount = round(price_usd / sol_price, 6)

    message = (
        f"💳 *Payment Instructions*\n\n"
        f"Plan: {plan}\n"
        f"Price: ${price_usd}\n\n"
        f"🔹 Pay with *Ethereum (ETH)*\n"
        f"Amount: `{eth_amount}` ETH\n"
        f"Address: `{RECEIVING_WALLETS['ETH']}`\n\n"
        f"🔹 Pay with *Solana (SOL)*\n"
        f"Amount: `{sol_amount}` SOL\n"
        f"Address: `{RECEIVING_WALLETS['SOL']}`\n\n"
        f"✅ After payment, our system will confirm automatically."
    )

    await update.callback_query.message.reply_text(message, parse_mode="Markdown")
