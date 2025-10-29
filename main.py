import os
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from fastapi import FastAPI
from blockchain import eth_is_confirmed, eth_get_tx, sol_get_balance

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


# --- Confirm Transaction Command ---
async def confirm_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a transaction hash.\nExample: /confirm 0x1234abcd...")
        return

    tx_hash = context.args[0].strip()

    # Try Ethereum first
    await update.message.reply_text("⏳ Checking transaction on Ethereum network...")
    eth_tx = eth_get_tx(tx_hash)
    if eth_tx:
        if eth_is_confirmed(tx_hash):
            await update.message.reply_text("✅ Ethereum transaction confirmed! Access granted.")
        else:
            await update.message.reply_text("⌛ Transaction found, waiting for more confirmations.")
        return

    # Try Solana
    await update.message.reply_text("🔄 Not Ethereum — checking Solana network...")
    try:
        bal = await sol_get_balance(tx_hash)
        if bal is not None:
            await update.message.reply_text(f"✅ Solana transaction confirmed! Balance: {bal:.4f} SOL")
        else:
            await update.message.reply_text("❌ Invalid Solana address or transaction.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error checking Solana: {e}")


# --- Telegram Bot Runner ---
def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("confirm", confirm_tx))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    print("🚀 Ice Premium Bot is now running...")
    app.run_polling()


# --- FastAPI Web App (for Render) ---
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Ice Premium Bot is live and running. Check Telegram to interact."}

@app.get("/health")
async def health():
    return {"status": "ok", "bot": "running"}


# --- Start Telegram bot in background ---
threading.Thread(target=run_bot).start()


# --- Local Test Mode ---
if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server for local test...")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
