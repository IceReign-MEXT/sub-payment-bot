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
import asyncio # New import for the fix

# =========================================================================
# FIX for APScheduler/AsyncIO compatibility with Uvicorn/Gunicorn
# Must be added at the top level before any async code runs.
if os.name != 'nt': # Checks if not Windows
    try:
        # Tries to use the high-performance uvloop if available
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except:
        # Fallback to the default policy fix if uvloop isn't installed
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
# =========================================================================

# Load environment variables
load_dotenv()

# --- Subscription Plans & Wallets ---
PLANS = {
    "basic": {"name": "💎 Basic", "price": "$10 / month"},
    "premium": {"name": "🔥 Premium", "price": "$25 / month"},
    "ultimate": {"name": "👑 Ultimate", "price": "$50 / month"},
}

# --- Track user wallet linking ---
USER_WALLETS = {}

# /start command
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

# /plans command
async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📜 *Available Plans:*\n\n"
    for key, plan in PLANS.items():
        text += f"{plan['name']} — {plan['price']}\n"
    text += "\nUse /start to select a plan."
    await update.message.reply_text(text, parse_mode="Markdown")

# Handle wallet linking
async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet_address = update.message.text.strip()
    USER_WALLETS[user_id] = wallet_address
    await update.message.reply_text(
        f"✅ Wallet address linked successfully:\n`{wallet_address}`",
        parse_mode="Markdown"
    )

# --- Telegram Bot Runner (The polling loop) ---
def run_bot():
    try:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
             print("!!! FATAL BOT ERROR: BOT_TOKEN is not set. Cannot start bot.")
             return

        app = Application.builder().token(bot_token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("plans", plans))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))

        print("🚀 Ice Premium Bot is now running...")
        app.run_polling()

    except Exception as e:
        # THIS WILL PRINT THE ERROR TO YOUR GUNICORN CONSOLE
        print(f"!!! FATAL BOT CONNECTION/STARTUP ERROR: {e}")
        # Re-raise the exception to stop the thread and alert the user
        raise


# --- FastAPI Web Application ---
# NOTE: The variable MUST be named 'app' for the Gunicorn command 'main:app'
app = FastAPI()

# FIX for 404 Not Found on root path ("/")
@app.get("/")
async def root():
    return {"message": "Ice Premium Bot is live and running. Check Telegram to interact."}

# Existing health check
@app.get("/health")
async def health():
    return {"status": "ok", "bot": "running"}


# --- Global Startup (Runs when Gunicorn imports the module) ---
# Starts the Telegram bot in a background thread
threading.Thread(target=run_bot).start()


# --- Main (Now only for local testing) ---
if __name__ == "__main__":
    # This block allows you to run 'python main.py' locally for testing
    print("Starting Uvicorn server for local test...")
    # Get port from env or default to 8000 for local testing
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
