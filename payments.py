import os
import requests
from config import SAFE_ETH_WALLET, SAFE_SOL_WALLET, CMC_API_KEY

CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

# Fetch crypto price from CoinMarketCap
def get_crypto_price(symbol: str):
    try:
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        params = {"symbol": symbol, "convert": "USD"}
        response = requests.get(CMC_URL, headers=headers, params=params)
        data = response.json()
        return float(data["data"][symbol]["quote"]["USD"]["price"])
    except Exception as e:
        print("❌ Price fetch error:", e)
        return None

# Generate a payment address for a user
def generate_payment_address(user_id, crypto="ETH"):
    if crypto.upper() == "ETH":
        return SAFE_ETH_WALLET
    elif crypto.upper() == "SOL":
        return SAFE_SOL_WALLET
    else:
        return None

# Check if a user paid the required amount
def check_payment(user_id, amount_usd, crypto="ETH", tx_hash_or_sig=None):
    from subscriptions import verify_eth_payment, verify_sol_payment

    if crypto.upper() == "ETH":
        if not tx_hash_or_sig:
            return False
        return verify_eth_payment(tx_hash_or_sig, amount_usd)
    elif crypto.upper() == "SOL":
        if not tx_hash_or_sig:
            return False
        return verify_sol_payment(tx_hash_or_sig, amount_usd)
    else:
        return False

# Send payment instructions to user
async def request_payment(update, context, plan: str, price_usd: float):
    eth_price = get_crypto_price("ETH")
    sol_price = get_crypto_price("SOL")

    if not eth_price or not sol_price:
        msg = "❌ Failed to fetch crypto prices. Try again later."
        if getattr(update, "callback_query", None):
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    eth_amount = round(price_usd / eth_price, 6)
    sol_amount = round(price_usd / sol_price, 6)

    message = (
        f"💳 *Payment Instructions*\n\n"
        f"Plan: {plan}\n"
        f"Price: ${price_usd}\n\n"
        f"🔹 Pay with *Ethereum (ETH)*\n"
        f"Amount: `{eth_amount}` ETH\n"
        f"Address: `{SAFE_ETH_WALLET}`\n\n"
        f"🔹 Pay with *Solana (SOL)*\n"
        f"Amount: `{sol_amount}` SOL\n"
        f"Address: `{SAFE_SOL_WALLET}`\n\n"
        f"✅ After payment, our system will confirm automatically."
    )

    if getattr(update, "callback_query", None):
        await update.callback_query.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")