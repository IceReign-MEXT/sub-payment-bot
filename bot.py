import os
import asyncio
import time
from datetime import datetime
import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

from web3 import Web3
from solana.rpc.async_api import AsyncClient as SolanaClient
import requests
from dotenv import load_dotenv

# -------------------- Load .env --------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
INFURA_KEY = os.getenv("INFURA_KEY")
CMC_API_KEY = os.getenv("CMC_API_KEY")
DATABASE_PATH = os.getenv("DATABASE_PATH", "subscriptions.db")

# -------------------- Database --------------------
conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
c = conn.cursor()

# Subscriptions
c.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT,
    plan TEXT,
    start_ts INTEGER,
    expires_ts INTEGER
)
""")

# Payments
c.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT,
    tx_hash TEXT,
    chain TEXT,
    amount REAL,
    plan TEXT,
    status TEXT,
    ts INTEGER
)
""")

# Pending payments
c.execute("""
CREATE TABLE IF NOT EXISTS pending_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT,
    plan TEXT,
    chain TEXT,
    expected_amount REAL,
    created_ts INTEGER,
    processed INTEGER DEFAULT 0
)
""")

conn.commit()

def add_subscription(telegram_id, plan, start_ts, expires_ts):
    c.execute(
        "INSERT INTO subscriptions (telegram_id, plan, start_ts, expires_ts) VALUES (?, ?, ?, ?)",
        (telegram_id, plan, int(start_ts), int(expires_ts))
    )
    conn.commit()

def get_latest_subscription(telegram_id):
    c.execute(
        "SELECT id, plan, start_ts, expires_ts FROM subscriptions WHERE telegram_id=? ORDER BY id DESC LIMIT 1",
        (telegram_id,)
    )
    row = c.fetchone()
    if not row:
        return None
    return {"id": row[0], "plan": row[1], "start_ts": row[2], "expires_ts": row[3]}

def add_pending_payment_request(telegram_id, plan, chain, expected_amount):
    c.execute(
        "INSERT INTO pending_payments (telegram_id, plan, chain, expected_amount, created_ts) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, plan, chain, float(expected_amount), int(time.time()))
    )
    conn.commit()

def get_pending_payment_requests(chain=None):
    if chain:
        c.execute("SELECT id, telegram_id, plan, chain, expected_amount FROM pending_payments WHERE processed=0 AND chain=?", (chain,))
    else:
        c.execute("SELECT id, telegram_id, plan, chain, expected_amount FROM pending_payments WHERE processed=0")
    rows = c.fetchall()
    return [{"id": r[0], "telegram_id": r[1], "plan": r[2], "chain": r[3], "expected_amount": r[4]} for r in rows]

def mark_payment_processed(pending_id):
    c.execute("UPDATE pending_payments SET processed=1 WHERE id=?", (pending_id,))
    conn.commit()

# -------------------- Web3 & Solana --------------------
w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))
sol_client = SolanaClient("https://api.mainnet-beta.solana.com")

def verify_eth_payment(tx_hash: str, amount_eth: float) -> bool:
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if tx.to and tx.to.lower() == SAFE_ETH_WALLET.lower():
            value_eth = w3.from_wei(tx.value, "ether")
            return value_eth >= amount_eth
    except Exception as e:
        print("❌ ETH verify error:", e)
    return False

async def verify_sol_payment(signature: str, amount_sol: float) -> bool:
    try:
        tx_resp = await sol_client.get_confirmed_transaction(signature)
        if tx_resp.get("result"):
            tx = tx_resp["result"]["transaction"]
            for instr in tx["message"]["instructions"]:
                parsed = instr.get("parsed")
                if parsed and parsed["info"]["destination"] == SAFE_SOL_WALLET:
                    lamports = int(parsed["info"]["lamports"])
                    sol_value = lamports / 10**9
                    return sol_value >= amount_sol
    except Exception as e:
        print("❌ SOL verify error:", e)
    return False

def get_crypto_price(symbol: str):
    try:
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        params = {"symbol": symbol, "convert": "USD"}
        resp = requests.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest", headers=headers, params=params)
        data = resp.json()
        return float(data["data"][symbol]["quote"]["USD"]["price"])
    except:
        return None

# -------------------- Subscription Plans --------------------
PLANS = {
    "Daily": {"price": 5, "duration": 1},
    "Weekly": {"price": 20, "duration": 7},
    "Monthly": {"price": 50, "duration": 30},
    "Yearly": {"price": 500, "duration": 365},
    "Lifetime": {"price": 1000, "duration": None},
}

# -------------------- Telegram Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💎 Sub-Payment Bot is online! Use /plans to subscribe.")

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{k} - ${v['price']}", callback_data=f"plan:{k}")] for k, v in PLANS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💎 Choose a subscription plan:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("plan:"):
        plan = query.data.split(":")[1]
        context.user_data["selected_plan"] = plan

        # generate amounts
        usd_amount = PLANS[plan]["price"]
        eth_price = get_crypto_price("ETH")
        sol_price = get_crypto_price("SOL")
        if not eth_price or not sol_price:
            await query.message.reply_text("❌ Failed to fetch crypto prices. Try again later.")
            return

        eth_amount = round(usd_amount / eth_price, 6)
        sol_amount = round(usd_amount / sol_price, 6)

        add_pending_payment_request(query.from_user.id, plan, "ETH", eth_amount)
        add_pending_payment_request(query.from_user.id, plan, "SOL", sol_amount)

        msg = f"💰 *Payment Instructions*\n\nPlan: {plan}\nPrice: ${usd_amount}\n\n" \
              f"🔹 Ethereum (ETH): `{eth_amount}` ETH\nAddress: `{SAFE_ETH_WALLET}`\n\n" \
              f"🔹 Solana (SOL): `{sol_amount}` SOL\nAddress: `{SAFE_SOL_WALLET}`\n\n" \
              "After sending, click /verify."
        await query.message.reply_text(msg, parse_mode="Markdown")

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = context.user_data.get("selected_plan")
    if not plan:
        await update.message.reply_text("⚠️ You have not selected a plan yet. Use /plans first.")
        return

    usd_amount = PLANS[plan]["price"]
    eth_pending = get_pending_payment_requests(chain="ETH")
    sol_pending = get_pending_payment_requests(chain="SOL")

    paid = False
    # Check ETH payments
    for req in eth_pending:
        if req["telegram_id"] == user_id:
            tx_hash = context.user_data.get("tx_hash")  # optional: user can provide
            if tx_hash and verify_eth_payment(tx_hash, req["expected_amount"]):
                mark_payment_processed(req["id"])
                paid = True
    # Check SOL payments
    for req in sol_pending:
        if req["telegram_id"] == user_id:
            tx_sig = context.user_data.get("tx_sig")  # optional
            if tx_sig and await verify_sol_payment(tx_sig, req["expected_amount"]):
                mark_payment_processed(req["id"])
                paid = True

    if paid:
        start_ts = int(time.time())
        duration = PLANS[plan]["duration"] or 9999
        expires_ts = start_ts + duration * 86400
        add_subscription(user_id, plan, start_ts, expires_ts)
        await update.message.reply_text(f"✅ Payment confirmed! You now have *{plan}* access.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Payment not detected yet. Make sure you sent the correct amount.")

# -------------------- Main --------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans_command))
    app.add_handler(CommandHandler("verify", verify_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("💎 Bot is running with polling...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())