import os
import sqlite3
from datetime import datetime, timedelta
import aiohttp
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# ------------------ Load environment ------------------
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
PREMIUM_CHANNEL_ID = int(os.getenv("PREMIUM_CHANNEL_ID"))
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID"))
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS", 365))
DEBUG = os.getenv("DEBUG", "False") == "True"

# ------------------ Database ------------------
conn = sqlite3.connect("subscriptions.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    tx_hash TEXT,
    start_date TEXT,
    end_date TEXT
)
""")
conn.commit()

# ------------------ FastAPI & Telegram ------------------
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# ------------------ Helper Functions ------------------
def add_subscription(user_id: int, tx_hash: str, days: int):
    start = datetime.utcnow()
    end = start + timedelta(days=days)
    c.execute("""
    INSERT OR REPLACE INTO subscriptions(user_id, tx_hash, start_date, end_date)
    VALUES (?, ?, ?, ?)
    """, (user_id, tx_hash, start.isoformat(), end.isoformat()))
    conn.commit()

def check_subscription(user_id: int):
    c.execute("SELECT end_date FROM subscriptions WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        return False
    end_date = datetime.fromisoformat(row[0])
    if datetime.utcnow() > end_date:
        # Auto remove user from premium channel
        try:
            application.bot.ban_chat_member(PREMIUM_CHANNEL_ID, user_id)
            application.bot.ban_chat_member(PREMIUM_GROUP_ID, user_id)
        except Exception:
            pass
        c.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
        conn.commit()
        return False
    return True

async def verify_payment(tx_hash: str):
    url = f"https://api.etherscan.io/api?module=transaction&action=gettxreceiptstatus&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            status = data.get("result", {}).get("status", "0")
            return status == "1"

# ------------------ User Commands ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 Welcome to Ice Premium Subscriptions!\n\n"
        "✅ Access premium content, tips, and exclusive resources.\n\n"
        "Commands:\n"
        "/plans – View plans\n"
        "/subscribe – Payment instructions\n"
        "/status – Check subscription"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 Subscription Plans\n\n"
        "• Monthly – $10 (30 days)\n"
        "• Lifetime – $50\n\n"
        "Use /subscribe to pay and get instant access."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💳 Payment Instructions:\n\n"
        f"Send ETH to: {PAYMENT_WALLET}\n"
        "After payment, send:\n"
        "/paid TX_HASH\n"
        "Subscription activates automatically."
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")
        return
    tx_hash = context.args[0]
    user_id = update.effective_user.id
    await update.message.reply_text("🔎 Verifying transaction, please wait...")

    success = await verify_payment(tx_hash)
    if success:
        add_subscription(user_id, tx_hash, MAX_SUB_DAYS)
        # Add user to premium channel/group
        try:
            await application.bot.unban_chat_member(PREMIUM_CHANNEL_ID, user_id)
            await application.bot.unban_chat_member(PREMIUM_GROUP_ID, user_id)
        except Exception:
            pass
        await update.message.reply_text("✅ Payment verified! Subscription activated.")
    else:
        await update.message.reply_text("❌ Payment not verified. Check your TX_HASH.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if check_subscription(user_id):
        await update.message.reply_text("✅ You have an active subscription!")
    else:
        await update.message.reply_text("❌ No active subscription.")

# ------------------ Admin Commands ------------------
async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /admin_verify USER_ID DAYS")
        return
    user_id = int(context.args[0])
    days = int(context.args[1])
    add_subscription(user_id, "MANUAL", days)
    await update.message.reply_text(f"✅ Subscription verified for {days} days.")

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /admin_cancel USER_ID")
        return
    user_id = int(context.args[0])
    c.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
    conn.commit()
    await update.message.reply_text(f"✅ Subscription cancelled for user {user_id}.")

# ------------------ Add Handlers ------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("admin_verify", admin_verify))
application.add_handler(CommandHandler("admin_cancel", admin_cancel))

# ------------------ FastAPI Webhook ------------------
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
