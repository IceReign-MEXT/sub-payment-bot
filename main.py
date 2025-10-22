import os
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from fastapi import FastAPI
import uvicorn
import asyncio
import random

# =========================================================================
# FIX for APScheduler/AsyncIO compatibility
import asyncio
if os.name != 'nt':
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
# =========================================================================

# Load environment variables
load_dotenv()

# --- Configuration (Uses the variables from your .env) ---
PLANS = {
    # Using specific prices/tokens based on high-value strategy
    "basic": {"name": "💎 Basic", "price": "0.005 ETH / month", "wallet": os.getenv("ETH_WALLET")},
    "premium": {"name": "🔥 Premium", "price": "0.1 SOL / month", "wallet": os.getenv("SOL_WALLET")},
}

# --- Telegram Bot Commands ---

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Welcome to the *Ice Premium Subscriptions* ❄️\n\n"
        "Use /buy to view available plans and start payment 💰"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# /buy command (The critical monetization command)
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📜 *Available Plans - Select One to Pay:*\n\n"
    for key, plan in PLANS.items():
        # Generates a pseudo-unique ID for tracking payment attempts
        payment_id = random.randint(100000, 999999)
        text += (
            f"/{key}_{payment_id} - {plan['name']} - {plan['price']}\n"
            f"Wallet: `{plan['wallet']}`\n\n"
        )
    text += "⚠️ *IMPORTANT*: Only send the exact crypto amount to the specified wallet."
    await update.message.reply_text(text, parse_mode="Markdown")

# --- Telegram Bot Runner (The polling loop) ---
def run_bot():
    try:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
             print("!!! FATAL BOT ERROR: BOT_TOKEN is not set. Cannot start bot.")
             return

        app = Application.builder().token(bot_token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("buy", buy))

        print("🚀 Minimal Payment Bot is now running...")
        app.run_polling()

    except Exception as e:
        print(f"!!! FATAL BOT CONNECTION/STARTUP ERROR: {e}")
        raise


# --- FastAPI Web Application (Health Check & Root) ---
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Minimal Payment Bot is LIVE. Use Telegram to access features."}

@app.get("/health")
async def health():
    return {"status": "ok", "bot": "running"}


# --- Global Startup (Runs when Gunicorn imports the module) ---
threading.Thread(target=run_bot).start()

# --- Main (Now only for local testing) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
