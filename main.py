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

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# --- Subscription Plans ---
PLANS = {
    "basic": {"name": "💎 Basic", "price": "$10 / month"},
    "premium": {"name": "🔥 Premium", "price": "$25 / month"},
    "ultimate": {"name": "👑 Ultimate", "price": "$50 / month"},
}

# --- Wallets for payment ---
ETH_WALLET = os.getenv("ETH_WALLET")
SOL_WALLET = os.getenv("SOL_WALLET")

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

# --- Telegram Bot Runner ---
def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    print("🚀 Ice Premium Bot is now running...")
    app.run_polling()

# --- FastAPI Health Check ---
app_web = FastAPI()

@app_web.get("/health")
async def health():
    return {"status": "ok", "bot": "running"}

# --- Main ---
if __name__ == "__main__":
    # Run Telegram bot in a separate thread
    threading.Thread(target=run_bot).start()
    
    # Run FastAPI web server for health checks
    uvicorn.run(app_web, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))