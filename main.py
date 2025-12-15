import os
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import sqlite3
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load environment
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
DEBUG = os.getenv("DEBUG") == "True"
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS"))
PREMIUM_CHANNEL_ID = int(os.getenv("PREMIUM_CHANNEL_ID"))
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID"))

# FastAPI App
app = FastAPI()

# Bot Setup
bot = Bot(TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

# Database
conn = sqlite3.connect("subscriptions.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    expiry TIMESTAMP
                )""")
conn.commit()

# Scheduler for auto-removal
scheduler = AsyncIOScheduler()

def check_expired_users():
    now = datetime.utcnow()
    cursor.execute("SELECT user_id, expiry FROM users")
    for user_id, expiry in cursor.fetchall():
        if expiry and datetime.fromisoformat(expiry) < now:
            try:
                bot.kick_chat_member(chat_id=PREMIUM_GROUP_ID, user_id=user_id)
            except Exception as e:
                print(f"Failed to remove {user_id}: {e}")
            cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()

scheduler.add_job(check_expired_users, "interval", minutes=5)
scheduler.start()

# ----------------------------
# Command Handlers
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 Welcome to Ice Premium Subscriptions!\n\n"
        "✅ Ice Premium Bot is live and ready to provide premium content.\n\n"
        "Commands:\n"
        "/plans - View subscription plans\n"
        "/subscribe - Payment instructions\n"
        "/status - Check your subscription"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 Subscription Plans:\n\n"
        "• Monthly – $10 (30 days)\n"
        "• Lifetime – $50\n\n"
        "Use /subscribe to pay and unlock premium content."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💳 Payment Instructions:\n\n"
        f"Send ETH to: {PAYMENT_WALLET}\n"
        "After payment, send /paid TX_HASH\n"
        "Subscription activates automatically."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT expiry FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        expiry = datetime.fromisoformat(row[0])
        await update.message.reply_text(f"✅ Active subscription until {expiry}")
    else:
        await update.message.reply_text("❌ No active subscription.")

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")
        return
    tx_hash = context.args[0]
    await update.message.reply_text("🔎 Verifying transaction, please wait...")
    # Call Etherscan API
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    r = requests.get(url).json()
    if r["result"] and r["result"]["to"].lower() == PAYMENT_WALLET.lower():
        # success
        user_id = update.effective_user.id
        expiry = datetime.utcnow() + timedelta(days=30)
        cursor.execute("INSERT OR REPLACE INTO users(user_id, expiry) VALUES (?, ?)", (user_id, expiry.isoformat()))
        conn.commit()
        # Add to premium channel/group
        try:
            await bot.unban_chat_member(chat_id=PREMIUM_GROUP_ID, user_id=user_id)
        except:
            pass
        await update.message.reply_text("✅ Payment verified! Subscription activated.")
    else:
        await update.message.reply_text("❌ Payment not found or invalid.")

# Admin verify manually
async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /admin_verify USER_ID DAYS")
        return
    user_id = int(context.args[0])
    days = int(context.args[1])
    expiry = datetime.utcnow() + timedelta(days=days)
    cursor.execute("INSERT OR REPLACE INTO users(user_id, expiry) VALUES (?, ?)", (user_id, expiry.isoformat()))
    conn.commit()
    await update.message.reply_text(f"✅ Subscription manually activated for {days} days.")

# ----------------------------
# Add Handlers
# ----------------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("admin_verify", admin_verify))

# ----------------------------
# FastAPI Webhook Endpoint
# ----------------------------
@app.post("/webhook")
async def webhook(req: Request):
    secret = req.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403)
    data = await req.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"status": "ok"}

# ----------------------------
# Startup
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
