import os
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from flask import Flask, jsonify

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
ETH_WALLET = "0x5B0703825e5299b52b0d00193Ac22E20795defBa"
SOL_WALLET = "HxmywH2gW9ezQ2nBXwurpaWsZS6YvdmLF23R9WgMAM7p"

# --- Track user wallet linking ---
USER_WALLETS = {}

# --- Commands ---
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
    for plan in PLANS.values():
        text += f"{plan['name']} — {plan['price']}\n"
    text += "\nUse /start to select a plan."
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data
    plan = PLANS.get(plan_key)
    if not plan:
        await query.edit_message_text("⚠️ Invalid selection. Try again.")
        return
    msg = (
        f"📌 You selected {plan['name']} ({plan['price']})\n\n"
        f"💼 *Payment Wallets:*\n"
        f"ETH: `{ETH_WALLET}`\n"
        f"SOL: `{SOL_WALLET}`\n\n"
        "💡 Send your wallet address below to link your account."
    )
    await query.edit_message_text(msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🆘 *Help Menu*\n\n"
        "/start — Begin and select your plan\n"
        "/plans — View available plans\n"
        "/help — Get this help message\n\n"
        "Just send your wallet address to link it 💳"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet_address = update.message.text.strip()
    USER_WALLETS[user_id] = wallet_address
    await update.message.reply_text(
        f"✅ Wallet address linked successfully:\n`{wallet_address}`",
        parse_mode="Markdown"
    )

# --- Flask health endpoint ---
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- Main Entry Point ---
def main():
    # Start Flask server in a separate thread
    threading.Thread(target=run_flask).start()

    # Start Telegram bot
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("plans", plans))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    telegram_app.add_handler(CallbackQueryHandler(handle_plan))

    print("🚀 Ice Premium Bot is now running...")
    telegram_app.run_polling()

if __name__ == "__main__":
    main()