import os
import sqlite3
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS", 365))

DB_FILE = "subscriptions.db"

app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# ---- Database Setup ----
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            expires_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---- Helper Functions ----
def add_subscription(user_id, username, days):
    expires_at = datetime.utcnow() + timedelta(days=days)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("REPLACE INTO subscriptions (user_id, username, expires_at) VALUES (?, ?, ?)",
              (user_id, username, expires_at.isoformat()))
    conn.commit()
    conn.close()

def check_subscription(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expires_at FROM subscriptions WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        expires_at = datetime.fromisoformat(row[0])
        if expires_at > datetime.utcnow():
            return (True, (expires_at - datetime.utcnow()).days)
    return (False, 0)

def verify_eth_payment(tx_hash, expected_wallet, expected_amount=None):
    """Verify ETH transaction via Etherscan"""
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return False
    result = resp.json().get("result")
    if not result:
        return False
    to_address = result.get("to", "").lower()
    if to_address != expected_wallet.lower():
        return False
    # Optional: check amount if provided
    if expected_amount:
        value = int(result.get("value", "0x0"), 16) / 10**18
        if value < expected_amount:
            return False
    return True

# ---- Telegram Commands ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Ice Premium Subscriptions Active!\n\nCommands:\n"
        "/plans - View plans\n"
        "/subscribe - Payment instructions\n"
        "/status - Check subscription"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 Subscription Plans\n\n"
        "• Monthly – $10 (30 days)\n"
        "• Lifetime – $50\n\n"
        "Use /subscribe to pay."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💳 Payment Instructions:\n\n"
        f"Send ETH to: {PAYMENT_WALLET}\n"
        "After payment, send:\n/paid TX_HASH\n"
        "Subscription activates automatically."
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")
        return
    tx_hash = args[0]

    await update.message.reply_text("🔎 Verifying transaction, please wait...")

    if verify_eth_payment(tx_hash, PAYMENT_WALLET):
        # For demo: default 30 days for monthly
        add_subscription(user_id, username, 30)
        await update.message.reply_text("✅ Payment verified! Subscription active for 30 days.")
    else:
        await update.message.reply_text("❌ Transaction could not be verified. Check TX hash.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    active, days_left = check_subscription(user_id)
    if active:
        await update.message.reply_text(f"✅ Active subscription: {days_left} days remaining.")
    else:
        await update.message.reply_text("❌ No active subscription.")

# ---- Admin Commands ----
async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /admin_verify USER_ID DAYS")
        return
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        add_subscription(user_id, "admin_added", days)
        await update.message.reply_text(f"✅ Subscription granted for {days} days to {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /admin_cancel USER_ID")
        return
    user_id = int(context.args[0])
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Subscription cancelled for {user_id}")

# ---- Add handlers ----
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("admin_verify", admin_verify))
application.add_handler(CommandHandler("admin_cancel", admin_cancel))

# ---- FastAPI webhook ----
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"ok": True}
