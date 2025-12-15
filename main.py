import os
import sqlite3
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS", 365))

app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# Initialize SQLite DB
DB_FILE = "subscriptions.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute(
    """CREATE TABLE IF NOT EXISTS subscriptions (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        expires_at TEXT
    )"""
)
conn.commit()

# ---- Helper functions ----
def get_subscription(user_id):
    c.execute("SELECT expires_at FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        expires_at = datetime.fromisoformat(row[0])
        return expires_at
    return None

def add_subscription(user_id, username, days):
    expires_at = datetime.now() + timedelta(days=days)
    c.execute(
        "INSERT OR REPLACE INTO subscriptions (user_id, username, expires_at) VALUES (?, ?, ?)",
        (user_id, username, expires_at.isoformat()),
    )
    conn.commit()

def cancel_subscription(user_id):
    c.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
    conn.commit()

def verify_eth_payment(tx_hash):
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    resp = requests.get(url).json()
    if resp.get("result"):
        tx = resp["result"]
        to_address = tx.get("to", "").lower()
        value_wei = int(tx.get("value", "0x0"), 16)
        if to_address == PAYMENT_WALLET.lower() and value_wei > 0:
            return True
    return False

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
        f"💳 Payment Instructions:\n\nSend ETH to: {PAYMENT_WALLET}\n"
        f"After payment, send:\n/paid TX_HASH\n"
        f"Subscription activates automatically."
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")
        return

    tx_hash = args[0]
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    verified = verify_eth_payment(tx_hash)
    if verified:
        add_subscription(user_id, username, MAX_SUB_DAYS)
        await update.message.reply_text(f"✅ Payment verified!\nSubscription active for {MAX_SUB_DAYS} days.")
    else:
        await update.message.reply_text("❌ Payment not found or incorrect. Please check your TX_HASH.")

    # Notify admin
    await application.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💰 Payment Submitted\nUser: {username}\nID: {user_id}\nTX: {tx_hash}\nVerified: {verified}",
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expires_at = get_subscription(user_id)
    if expires_at and expires_at > datetime.now():
        await update.message.reply_text(f"✅ Active subscription\nExpires at: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        await update.message.reply_text("❌ No active subscription.")

# ---- Admin Commands ----
async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /admin_verify USER_ID DAYS")
        return
    user_id = int(args[0])
    days = int(args[1])
    username = f"user_{user_id}"
    add_subscription(user_id, username, days)
    await update.message.reply_text(f"✅ Subscription for {user_id} activated for {days} days.")

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /admin_cancel USER_ID")
        return
    user_id = int(args[0])
    cancel_subscription(user_id)
    await update.message.reply_text(f"❌ Subscription for {user_id} canceled.")

async def subscriptions_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    c.execute("SELECT user_id, username, expires_at FROM subscriptions")
    rows = c.fetchall()
    if not rows:
        await update.message.reply_text("No active subscriptions.")
        return
    message = "📃 Active Subscriptions:\n"
    for uid, username, expires_at in rows:
        message += f"{uid} | {username} | Expires: {expires_at}\n"
    await update.message.reply_text(message)

# ---- Add handlers ----
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("admin_verify", admin_verify))
application.add_handler(CommandHandler("admin_cancel", admin_cancel))
application.add_handler(CommandHandler("subscriptions", subscriptions_list))

# ---- FastAPI Webhook ----
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
