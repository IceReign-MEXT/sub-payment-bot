import os
import sqlite3
import logging
import asyncio
import requests
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# =============================
# ENV
# =============================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

PAYMENT_WALLET = os.getenv("PAYMENT_WALLET").lower()
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")

PREMIUM_CHANNEL_ID = int(os.getenv("PREMIUM_CHANNEL_ID"))
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID"))

PRICE_MONTHLY = 10
PRICE_LIFETIME = 50

# =============================
# LOGGING
# =============================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("SUBBOT")

# =============================
# DATABASE
# =============================
conn = sqlite3.connect("subscriptions.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    expires_at TEXT,
    lifetime INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS payments (
    tx_hash TEXT PRIMARY KEY,
    user_id INTEGER,
    amount REAL,
    created_at TEXT
)
""")
conn.commit()

# =============================
# BOT / API
# =============================
bot = Bot(TOKEN)
tg_app = Application.builder().token(TOKEN).build()
api = FastAPI()

# =============================
# HELPERS
# =============================
def now():
    return datetime.now(timezone.utc)

def is_active(user_id):
    cur.execute("SELECT expires_at, lifetime FROM subscriptions WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        return False
    expires, lifetime = row
    if lifetime:
        return True
    return datetime.fromisoformat(expires) > now()

def activate(user_id, days=0, lifetime=False):
    if lifetime:
        cur.execute("REPLACE INTO subscriptions VALUES (?, ?, 1)", (user_id, now().isoformat()))
    else:
        exp = now() + timedelta(days=days)
        cur.execute("REPLACE INTO subscriptions VALUES (?, ?, 0)", (user_id, exp.isoformat()))
    conn.commit()

def record_payment(tx, user_id, amount):
    cur.execute("INSERT OR IGNORE INTO payments VALUES (?, ?, ?, ?)", (tx, user_id, amount, now().isoformat()))
    conn.commit()

def tx_used(tx):
    cur.execute("SELECT 1 FROM payments WHERE tx_hash=?", (tx,))
    return cur.fetchone() is not None

# =============================
# ETH VERIFICATION
# =============================
def verify_tx(tx_hash):
    url = "https://api.etherscan.io/api"
    params = {
        "module": "proxy",
        "action": "eth_getTransactionByHash",
        "txhash": tx_hash,
        "apikey": ETHERSCAN_KEY
    }
    r = requests.get(url, params=params, timeout=15).json()
    tx = r.get("result")
    if not tx:
        return None
    to_addr = tx["to"]
    value = int(tx["value"], 16) / 1e18
    if not to_addr or to_addr.lower() != PAYMENT_WALLET:
        return None
    return value

# =============================
# COMMANDS
# =============================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 *Premium Access Bot*\n\n"
        "Automated • Secure • Instant\n\n"
        "/plans – Prices\n"
        "/subscribe – How to pay\n"
        "/status – Check access",
        parse_mode="Markdown"
    )

async def plans(update: Update, ctx):
    await update.message.reply_text(
        f"💼 *Plans*\n\n"
        f"• Monthly – ${PRICE_MONTHLY}\n"
        f"• Lifetime – ${PRICE_LIFETIME}\n\n"
        "Crypto only. Instant access.",
        parse_mode="Markdown"
    )

async def subscribe(update: Update, ctx):
    await update.message.reply_text(
        f"💳 *Payment*\n\n"
        f"Send ETH to:\n`{PAYMENT_WALLET}`\n\n"
        f"Then submit:\n`/paid TX_HASH`\n\n"
        f"Monthly: ${PRICE_MONTHLY}\n"
        f"Lifetime: ${PRICE_LIFETIME}",
        parse_mode="Markdown"
    )

async def paid(update: Update, ctx):
    if len(ctx.args) != 1:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")
        return
    tx = ctx.args[0]
    user_id = update.effective_user.id
    if tx_used(tx):
        await update.message.reply_text("❌ Transaction already used.")
        return
    await update.message.reply_text("🔎 Verifying payment...")
    value = verify_tx(tx)
    if not value:
        await update.message.reply_text("❌ Invalid or unconfirmed transaction.")
        return
    record_payment(tx, user_id, value)
    if value >= PRICE_LIFETIME / 3000:
        activate(user_id, lifetime=True)
    elif value >= PRICE_MONTHLY / 3000:
        activate(user_id, days=30)
    else:
        await update.message.reply_text("❌ Amount too low.")
        return
    try:
        await bot.invite_chat_member(PREMIUM_CHANNEL_ID, user_id)
        await bot.invite_chat_member(PREMIUM_GROUP_ID, user_id)
    except:
        pass
    await update.message.reply_text("✅ Access granted. Welcome.")

async def status(update: Update, ctx):
    await update.message.reply_text("✅ Active" if is_active(update.effective_user.id) else "❌ Not active")

# =============================
# AUTO CLEANUP
# =============================
async def cleanup_task():
    while True:
        cur.execute("SELECT user_id FROM subscriptions WHERE lifetime=0 AND expires_at < ?", (now().isoformat(),))
        expired = cur.fetchall()
        for (uid,) in expired:
            try:
                await bot.ban_chat_member(PREMIUM_CHANNEL_ID, uid)
                await bot.unban_chat_member(PREMIUM_CHANNEL_ID, uid)
            except:
                pass
            cur.execute("DELETE FROM subscriptions WHERE user_id=?", (uid,))
            conn.commit()
        await asyncio.sleep(3600)

# =============================
# WEBHOOK
# =============================
@api.post("/webhook")
async def webhook(req: Request):
    if WEBHOOK_SECRET:
        if req.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            raise HTTPException(403)
    data = await req.json()
    await tg_app.process_update(Update.de_json(data, bot))
    return {"ok": True}

@api.get("/health")
def health():
    return {"status": "ok"}

# =============================
# STARTUP
# =============================
@api.on_event("startup")
async def startup():
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("plans", plans))
    tg_app.add_handler(CommandHandler("subscribe", subscribe))
    tg_app.add_handler(CommandHandler("paid", paid))
    tg_app.add_handler(CommandHandler("status", status))
    await tg_app.initialize()
    await tg_app.start()
    asyncio.create_task(cleanup_task())
