import os
import sqlite3
from datetime import datetime, timedelta
import aiohttp
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Environment Variables
# -----------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS", 365))

# -----------------------------
# FastAPI & Telegram Setup
# -----------------------------
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# -----------------------------
# SQLite Setup
# -----------------------------
conn = sqlite3.connect("subscriptions.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    plan TEXT,
    start_date TEXT,
    end_date TEXT
)
""")
conn.commit()

# -----------------------------
# Helper Functions
# -----------------------------
def get_subscription(user_id):
    cursor.execute("SELECT * FROM subscriptions WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def activate_subscription(user_id, username, plan, days):
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=days)
    cursor.execute("""
    INSERT OR REPLACE INTO subscriptions (user_id, username, plan, start_date, end_date)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, plan, start_date.isoformat(), end_date.isoformat()))
    conn.commit()

def is_active(user_id):
    sub = get_subscription(user_id)
    if sub:
        end_date = datetime.fromisoformat(sub[4])
        return datetime.utcnow() < end_date
    return False

async def verify_eth_payment(tx_hash: str, amount_eth: float):
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            tx = data.get("result")
            if not tx:
                return False
            to_address = tx.get("to")
            value_wei = int(tx.get("value", "0x0"), 16)
            value_eth = value_wei / 10**18
            return to_address.lower() == PAYMENT_WALLET.lower() and value_eth >= amount_eth

# -----------------------------
# Telegram Commands
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Ice Premium Subscriptions Active!\n\n"
        "Commands:\n"
        "/plans – View plans\n"
        "/subscribe – Payment instructions\n"
        "/status – Check subscription"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 Subscription Plans:\n\n"
        "• Monthly – $10 (30 days)\n"
        "• Lifetime – $50\n\n"
        "Use /subscribe to pay."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💳 Payment Instructions:\n\n"
        f"Send payment to ETH wallet:\n\n"
        f"{PAYMENT_WALLET}\n\n"
        "After payment, send:\n/paid TX_HASH\n"
        "Admin will verify automatically."
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if len(context.args) == 0:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")
        return
    tx_hash = context.args[0]
    # Determine amount based on plan selection (simplified: Monthly $10)
    amount_eth = 0.003  # Example: set according to ETH/USD
    verified = await verify_eth_payment(tx_hash, amount_eth)
    if verified:
        activate_subscription(user.id, user.username, "Monthly", 30)
        await update.message.reply_text("✅ Payment verified! Subscription active.")
        # Notify admin
        await application.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 New verified payment:\nUser: {user.username}\nID: {user.id}\nTX: {tx_hash}"
        )
    else:
        await update.message.reply_text("❌ Payment could not be verified. Check TX_HASH or amount.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_active(user.id):
        sub = get_subscription(user.id)
        end_date = datetime.fromisoformat(sub[4])
        await update.message.reply_text(
            f"✅ Subscription Active\nPlan: {sub[2]}\nExpires: {end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
    else:
        await update.message.reply_text("❌ No active subscription.")

# -----------------------------
# Admin Commands
# -----------------------------
async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not admin.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /admin_verify USER_ID DAYS")
        return
    target_id = int(context.args[0])
    days = int(context.args[1])
    activate_subscription(target_id, "manual", "Admin", days)
    await update.message.reply_text(f"✅ User {target_id} subscription activated for {days} days.")

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not admin.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: /admin_cancel USER_ID")
        return
    target_id = int(context.args[0])
    cursor.execute("DELETE FROM subscriptions WHERE user_id=?", (target_id,))
    conn.commit()
    await update.message.reply_text(f"✅ User {target_id} subscription cancelled.")

# -----------------------------
# Add handlers
# -----------------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("admin_verify", admin_verify))
application.add_handler(CommandHandler("admin_cancel", admin_cancel))

# -----------------------------
# FastAPI Webhook
# -----------------------------
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
    )

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"ok": True}
