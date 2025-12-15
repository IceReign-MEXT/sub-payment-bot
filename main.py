import os
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import sqlite3

# -----------------------------
# Load environment
# -----------------------------
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS", 365))
PREMIUM_CHANNEL_ID = int(os.getenv("PREMIUM_CHANNEL_ID"))
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID"))

DB_FILE = "subscriptions.db"

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------
# Database
# -----------------------------
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute(
    """CREATE TABLE IF NOT EXISTS subscriptions (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        expiry TIMESTAMP
    )"""
)
conn.commit()

# -----------------------------
# Helper functions
# -----------------------------
def add_subscription(user_id, username, days):
    expiry = datetime.utcnow() + timedelta(days=days)
    c.execute(
        "INSERT OR REPLACE INTO subscriptions(user_id, username, expiry) VALUES (?, ?, ?)",
        (user_id, username, expiry)
    )
    conn.commit()

def remove_subscription(user_id):
    c.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
    conn.commit()

def check_subscription(user_id):
    c.execute("SELECT expiry FROM subscriptions WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        return datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f") > datetime.utcnow()
    return False

def get_expired_users():
    c.execute("SELECT user_id FROM subscriptions WHERE expiry<=?", (datetime.utcnow(),))
    return [row[0] for row in c.fetchall()]

def verify_eth_tx(tx_hash, address=PAYMENT_WALLET):
    """Verify ETH transaction via Etherscan API"""
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    r = requests.get(url).json()
    result = r.get("result")
    if not result:
        return False
    to_addr = result.get("to")
    value = int(result.get("value", "0"), 16) / 10 ** 18
    return to_addr.lower() == address.lower() and value > 0

# -----------------------------
# Command Handlers
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"💎 Welcome to Ice Premium Subscriptions!\n\n"
        f"✅ Bot is live and ready to provide premium content, tips, and resources.\n\n"
        f"Commands:\n"
        f"/plans – View subscription plans\n"
        f"/subscribe – Payment instructions\n"
        f"/status – Check subscription"
    )
    await update.message.reply_text(msg)

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"💼 Subscription Plans:\n\n"
        f"• Monthly – $10 (30 days)\n"
        f"• Lifetime – $50\n\n"
        f"Use /subscribe to get payment instructions and unlock premium content."
    )
    await update.message.reply_text(msg)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"💳 Payment Instructions:\n\n"
        f"Send ETH to: {PAYMENT_WALLET}\n"
        f"After payment, send:\n"
        f"/paid TX_HASH\n"
        f"Subscription activates automatically."
    )
    await update.message.reply_text(msg)

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tx_hash = context.args[0]
        await update.message.reply_text(f"🔎 Verifying transaction {tx_hash}...")
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.first_name
        if verify_eth_tx(tx_hash):
            add_subscription(user_id, username, 30)  # 30 days by default
            await update.message.reply_text("✅ Payment verified! Subscription activated.")
            await context.bot.add_chat_member(PREMIUM_CHANNEL_ID, user_id)
        else:
            await update.message.reply_text("❌ Transaction not valid or not sent to correct wallet.")
    except IndexError:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if check_subscription(user_id):
        await update.message.reply_text("✅ You have an active subscription.")
    else:
        await update.message.reply_text("❌ No active subscription.")

async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        username = "Admin"  # optional
        add_subscription(user_id, username, days)
        await update.message.reply_text(f"✅ Subscription for {user_id} verified for {days} days.")
        await context.bot.add_chat_member(PREMIUM_CHANNEL_ID, user_id)
    except:
        await update.message.reply_text("❌ Usage: /admin_verify USER_ID DAYS")

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        remove_subscription(user_id)
        await update.message.reply_text(f"✅ Subscription for {user_id} canceled.")
        await context.bot.ban_chat_member(PREMIUM_CHANNEL_ID, user_id)
        await context.bot.unban_chat_member(PREMIUM_CHANNEL_ID, user_id)
    except:
        await update.message.reply_text("❌ Usage: /admin_cancel USER_ID")

# -----------------------------
# Scheduler for expired users
# -----------------------------
async def remove_expired_users(app):
    expired_users = get_expired_users()
    for user_id in expired_users:
        remove_subscription(user_id)
        try:
            await app.bot.ban_chat_member(PREMIUM_CHANNEL_ID, user_id)
            await app.bot.unban_chat_member(PREMIUM_CHANNEL_ID, user_id)
            logger.info(f"Removed expired subscription: {user_id}")
        except:
            logger.warning(f"Failed to remove user: {user_id}")

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("plans", plans))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("paid", paid))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("admin_verify", admin_verify))
    application.add_handler(CommandHandler("admin_cancel", admin_cancel))

    # Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(remove_expired_users, "interval", minutes=10, args=[application])
    scheduler.start()

    # Webhook
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting bot on port {port}")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=WEBHOOK_SECRET,
        webhook_url=f"{WEBHOOK_URL}/{WEBHOOK_SECRET}"
    )
