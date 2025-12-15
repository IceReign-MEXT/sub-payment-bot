import os
import aiosqlite
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET")

DB_FILE = "subscriptions.db"

app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# ---------------- DATABASE ----------------
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT
            )
        """)
        await db.commit()

async def set_subscription(user_id: int, days: int):
    expires = datetime.utcnow() + timedelta(days=days)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "REPLACE INTO subscriptions (user_id, expires_at) VALUES (?, ?)",
            (user_id, expires.isoformat())
        )
        await db.commit()

async def get_subscription(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT expires_at FROM subscriptions WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return datetime.fromisoformat(row[0])

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ *Subscription Bot Active*\n\n"
        "Commands:\n"
        "/plans – View plans\n"
        "/subscribe – Payment instructions\n"
        "/status – Check subscription",
        parse_mode="Markdown"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 *Subscription Plans*\n\n"
        "• Monthly – $10 (30 days)\n"
        "• Lifetime – $50\n\n"
        "Use /subscribe to pay.",
        parse_mode="Markdown"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 *Payment Instructions*\n\n"
        f"Send payment to ETH wallet:\n\n`{PAYMENT_WALLET}`\n\n"
        "After payment, send:\n"
        "`/paid TX_HASH`\n\n"
        "Admin will verify manually.",
        parse_mode="Markdown"
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /paid TX_HASH")
        return

    tx = context.args[0]
    user = update.message.from_user

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "💰 *New Payment Submitted*\n\n"
            f"User: {user.full_name}\n"
            f"ID: `{user.id}`\n"
            f"TX: `{tx}`"
        ),
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ Payment submitted.\n\n"
        "Verification in progress."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sub = await get_subscription(update.message.from_user.id)
    if not sub:
        await update.message.reply_text("❌ No active subscription.")
        return

    if sub < datetime.utcnow():
        await update.message.reply_text("⚠️ Subscription expired.")
        return

    await update.message.reply_text(
        f"✅ Active until:\n{sub.strftime('%Y-%m-%d %H:%M UTC')}"
    )

async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /admin_verify USER_ID DAYS"
        )
        return

    user_id = int(context.args[0])
    days = int(context.args[1])

    await set_subscription(user_id, days)
    await update.message.reply_text(
        f"✅ User {user_id} verified for {days} days."
    )

# ---------------- HANDLERS ----------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("plans", plans))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("paid", paid))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("admin_verify", admin_verify))

# ---------------- FASTAPI ----------------
@app.on_event("startup")
async def startup():
    await init_db()
    await application.initialize()
    await application.bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET
    )

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"ok": True}
