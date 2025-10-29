import os
import asyncio
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from fastapi import FastAPI, Request, HTTPException

# NOTE: Your blockchain.py and utils.py are imported implicitly
# if your handlers need them, but they are not shown here.

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
# Use os.environ.get for security and compatibility with Render's environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# MUST be your exact Render URL: https://sub-payment-bot-2-q0rr.onrender.com
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://sub-payment-bot-2-q0rr.onrender.com") 

if not BOT_TOKEN:
    # In a real app, you'd handle this more gracefully
    raise ValueError("BOT_TOKEN environment variable is not set.")

# --- SUBSCRIPTION PLANS (Assuming these are correct from your files) ---
PLANS = {
    "basic": {"name": "💎 Basic", "price": "$10 / month"},
    "premium": {"name": "🔥 Premium", "price": "$25 / month"},
    "ultimate": {"name": "👑 Ultimate", "price": "$50 / month"},
}
USER_WALLETS = {}

# === TELEGRAM HANDLERS (Assuming your existing logic is correct) ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"👋 Welcome, *{user.first_name or 'User'}!*\n\n"
        "Welcome to *Ice Premium Subscriptions* ❄️\n\n"
        "🔥 Get access to premium features:\n"
        "— Secure blockchain payments\n"
        "— Auto-renewal options\n"
        "— Multi-chain support\n\n"
        "Use /plans to view available plans 💎"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📜 *Available Plans:*\n\n"
    for key, plan in PLANS.items():
        text += f"{plan['name']} — {plan['price']}\n"
    text += "\nUse /start to select a plan."
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet_address = update.message.text.strip()
    USER_WALLETS[user_id] = wallet_address
    await update.message.reply_text(
        f"✅ Wallet address linked successfully:\n`{wallet_address}`",
        parse_mode="Markdown"
    )

# === BOT APPLICATION SETUP ===
bot_app = Application.builder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("plans", plans))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))

# === FASTAPI WEB APP SETUP ===
app = FastAPI()

# 1. Startup Event: Initialize bot and set the webhook
@app.on_event("startup")
async def startup_event():
    await bot_app.initialize()
    # CRITICAL: Set the webhook URL on bot startup
    await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    await bot_app.start()

# 2. Shutdown Event
@app.on_event("shutdown")
async def shutdown_event():
    await bot_app.shutdown()

# 3. WEBHOOK ROUTE (The entry point for all Telegram messages)
@app.post("/")
async def telegram_webhook(request: Request):
    """Handles incoming Telegram updates via POST request."""
    try:
        update_json = await request.json()
        update = Update.de_json(update_json, bot_app.bot)
        # Process the update using the bot application
        await bot_app.process_update(update)
        # MUST return 200 OK quickly for Telegram
        return {"status": "ok"}
    except Exception as e:
        # Log the error for debugging, but still return 200
        print(f"Error processing update: {e}")
        return {"status": "ok"}

# 4. Root/Health Check Routes
@app.get("/")
async def root():
    return {"message": "Ice Premium Bot is live and ready for webhooks. Send /start in Telegram."}

@app.get("/health")
async def health():
    return {"status": "ok", "bot_running": bot_app.running}
