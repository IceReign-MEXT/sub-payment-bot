import os
import datetime
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv
import aiohttp
import sqlite3

load_dotenv()

# ---- ENV ----
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
MAX_SUB_DAYS = int(os.getenv("MAX_SUB_DAYS", 365))

# ---- DATABASE ----
conn = sqlite3.connect("subscriptions.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    plan TEXT,
    expires_at TEXT
)
""")
conn.commit()

# ---- FastAPI ----
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# ---- Helper Functions ----
def is_subscribed(user_id):
    c.execute("SELECT expires_at FROM subscriptions WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        expires_at = datetime.datetime.fromisoformat(row[0])
        return expires_at > datetime.datetime.utcnow()
    return False

def get_subscription_info(user_id):
    c.execute("SELECT plan, expires_at FROM subscriptions WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        plan, expires_at = row
        return plan, expires_at
    return None, None

async def verify_payment(tx_hash):
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            # Basic validation: check tx exists and to-address matches
            if "result" in data and data["result"]:
                to_address = data["result"]["to"]
                if to_address and to_address.lower() == PAYMENT_WALLET.lower():
                    return True
    return False

def add_subscription(user_id, username, plan, days):
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    c.execute("""
    INSERT OR REPLACE INTO subscriptions(user_id, username, plan, expires_at)
    VALUES (?, ?, ?, ?)
    """, (user_id, username, plan, expires_at.isoformat()))
    conn.commit()

# ---- Command Handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💎 *Welcome to Ice Premium Subscriptions!*\n\n"
        "✅ Ice Premium Bot is live and ready to provide you with premium content, exclusive tips, and professional resources.\n\n"
        "*Commands to get started:*\n"
        "/plans – View subscription plans\n"
        "/subscribe – Payment instructions\n"
        "/status – Check your subscription\n\n"
        "*Subscription Plans:*\n"
        "• Monthly – $10 (30 days)\n"
        "• Lifetime – $50\n\n"
        "Use /subscribe to pay and unlock premium content instantly.\n\n"
        "🔒 All payments are ETH-based and auto-verified via blockchain. Admin can manually verify if needed."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💼 *Subscription Plans*\n\n"
        "• Monthly – $10 (30 days)\n"
        "• Lifetime – $50\n\n"
        "Use /subscribe to get payment instructions and unlock your premium content instantly."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 *Payment Instructions*\n\n"
        f"Send ETH to: `{PAYMENT_WALLET}`\n\n"
        "After payment, submit your transaction hash with:\n"
        "/paid TX_HASH\n\n"
        "Your subscription and premium content will activate automatically."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: /paid TX_HASH\nPlease provide your Ethereum transaction hash.")
        return
    tx_hash = args[0]
    await update.message.reply_text("🔎 Verifying transaction, please wait...")
    if await verify_payment(tx_hash):
        plan = "Monthly"  # default, can extend to detect custom amounts
        days = 30
        add_subscription(user_id, username, plan, days)
        # Send premium content automatically
        premium_text = (
            "🎉 *Payment Verified!*\n\n"
            "Welcome to your premium content area.\n\n"
            "Here is your first exclusive tip:\n"
            "_“Top strategies to maximize your Ice Premium experience…”_\n\n"
            "Use the following commands to access more content:\n"
            "/content1 – First set of tips\n"
            "/content2 – Second set of resources\n"
            "/exclusive – Exclusive premium content\n\n"
            "Enjoy your subscription!"
        )
        await update.message.reply_text(premium_text, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Transaction verification failed. Check your TX_HASH and try again.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if is_subscribed(user_id):
        plan, expires_at = get_subscription_info(user_id)
        text = f"✅ Subscription Active!\nPlan: {plan}\nExpires: {expires_at}"
    else:
        text = "❌ No active subscription.\nUse /subscribe to pay and activate your subscription."
    await update.message.reply_text(text)

# ---- Premium Content Commands ----
async def content1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_subscribed(user_id):
        await update.message.reply_text("❌ You must have an active subscription to access this content. Use /subscribe.")
        return
    text = (
        "📘 *Premium Content 1*\n\n"
        "Here are your first exclusive tips for Ice Premium users...\n"
        "1️⃣ Tip 1\n2️⃣ Tip 2\n3️⃣ Tip 3\n\n"
        "Use /content2 for more!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def content2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_subscribed(user_id):
        await update.message.reply_text("❌ You must have an active subscription to access this content. Use /subscribe.")
        return
    text = (
        "📘 *Premium Content 2*\n\n"
        "Here are the next set of professional resources and strategies...\n"
        "1️⃣ Resource A\n2️⃣ Resource B\n3️⃣ Resource C\n\n"
        "Use /exclusive for exclusive tips!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def exclusive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_subscribed(user_id):
        await update.message.reply_text("❌ You must have an active subscription to access this content. Use /subscribe.")
        return
    text = (
        "🌟 *Exclusive Premium Content*\n\n"
        "Congratulations! Here is your exclusive professional content for Ice Premium subscribers only.\n"
        "🔥 Advanced tips, guides, and strategies to maximize your experience.\n\n"
        "Enjoy and make the most of your subscription!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ---- Admin Commands ----
async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Usage: /admin_verify USER_ID DAYS")
        return
    target_id = int(args[0])
    days = int(args[1])
    add_subscription(target_id, "manual", "AdminPlan", days)
    await update.message.reply_text(f"✅ User {target_id} manually verified for {days} days.")

# ---- Register Handlers ----
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("content1", content1))
application.add_handler(CommandHandler("content2", content2))
application.add_handler(CommandHandler("exclusive", exclusive))
application.add_handler(CommandHandler("admin_verify", admin_verify))

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
