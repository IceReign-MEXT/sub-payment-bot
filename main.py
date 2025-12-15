import os
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
PREMIUM_CHANNEL_ID = int(os.getenv("PREMIUM_CHANNEL_ID"))
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID"))
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS", 365))

# -----------------------------
# FastAPI & Telegram App
# -----------------------------
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# -----------------------------
# In-Memory Subscriptions
# {user_id: expiry_datetime}
# -----------------------------
active_subscriptions = {}

# -----------------------------
# Telegram Commands
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Welcome to *Ice Premium Subscriptions* ✨\n\n"
        "✅ *Your gateway to exclusive content and premium access!*\n\n"
        "*Commands Available:*\n"
        "/plans - View subscription plans\n"
        "/subscribe - How to pay & get access\n"
        "/status - Check your subscription\n\n"
        "💎 Join the premium experience now!",
        parse_mode="Markdown"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 *Ice Premium Subscription Plans*\n\n"
        "💰 *Monthly*: $10 – 30 days of premium access\n"
        "💎 *Lifetime*: $50 – Unlimited access\n\n"
        "⚡ Use /subscribe to pay and get instant access!\n"
        "🔥 Premium content, support, and updates delivered directly to you.",
        parse_mode="Markdown"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💳 *Payment Instructions*\n\n"
        f"Send Ethereum (ETH) to the wallet below:\n"
        f"`{PAYMENT_WALLET}`\n\n"
        "After payment, send the transaction hash using:\n"
        "/paid TX_HASH\n\n"
        "⏱ *Your subscription activates automatically upon verification!*",
        parse_mode="Markdown"
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.message.from_user.id
    if not args:
        await update.message.reply_text("❌ *Usage:* /paid TX_HASH", parse_mode="Markdown")
        return

    tx_hash = args[0]
    await update.message.reply_text("🔎 *Verifying transaction, please wait...*", parse_mode="Markdown")

    # -----------------------------
    # Demo verification: assume success
    # You can integrate ETHERSCAN_KEY here
    # -----------------------------
    expiry = datetime.utcnow() + timedelta(days=MAX_SUB_DAYS)
    active_subscriptions[user_id] = expiry

    # Add user to channel/group
    try:
        await application.bot.unban_chat_member(PREMIUM_CHANNEL_ID, user_id)
        await application.bot.unban_chat_member(PREMIUM_GROUP_ID, user_id)
    except:
        pass

    await update.message.reply_text(
        "✅ *Payment verified!*\n"
        f"🎉 You now have access for *{MAX_SUB_DAYS} days*.\n"
        "💎 Enjoy your premium content!",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    expiry = active_subscriptions.get(user_id)
    if expiry and expiry > datetime.utcnow():
        days_left = (expiry - datetime.utcnow()).days
        await update.message.reply_text(
            f"✅ *Active subscription*\n"
            f"⏳ Days remaining: *{days_left}*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ *No active subscription*\n"
            "Use /subscribe to get premium access immediately.",
            parse_mode="Markdown"
        )

# -----------------------------
# Auto-remove expired users
# -----------------------------
async def remove_expired_users():
    while True:
        now = datetime.utcnow()
        for user_id, expiry in list(active_subscriptions.items()):
            if expiry <= now:
                try:
                    await application.bot.ban_chat_member(PREMIUM_CHANNEL_ID, user_id)
                    await application.bot.ban_chat_member(PREMIUM_GROUP_ID, user_id)
                except:
                    pass
                del active_subscriptions[user_id]
        await asyncio.sleep(3600)  # check every hour

# -----------------------------
# Register Command Handlers
# -----------------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("status", status))

# -----------------------------
# FastAPI Webhook
# -----------------------------
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    asyncio.create_task(remove_expired_users())

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"ok": True}
