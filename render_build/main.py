import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Subscription plans
PLANS = {
    "Daily": "💸 Daily Plan",
    "Weekly": "💵 Weekly Plan",
    "Monthly": "💰 Monthly Plan",
    "Yearly": "💎 Yearly Plan",
    "Lifetime": "👑 Lifetime Plan"
}

# Wallet addresses (for now, testing mode)
ETH_WALLET = "0x5B0703825e5299b52b0d00193Ac22E20795defBa"
SOL_WALLET = "HxmywH2gW9ezQ2nBXwurpaWsZS6YvdmLF23R9WgMAM7p"

USER_WALLETS = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Welcome to *Ice Premium Subscriptions!*\n\n"
        "✨ Choose your plan\n"
        "⚡ Fast & secure payments\n"
        "📩 Instant activation\n\n"
        "Use /plans to view available plans 🚀"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# /plans command
async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(plan, callback_data=plan)] for plan in PLANS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 Choose your subscription plan below:", reply_markup=reply_markup)

# Handle plan selection
async def handle_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_name = query.data
    await query.edit_message_text(
        text=(
            f"📌 You selected {PLANS[plan_name]}\n\n"
            f"💼 *Payment Wallet (Testing Mode)*\n"
            f"ETH: `{ETH_WALLET}`\n"
            f"SOL: `{SOL_WALLET}`\n\n"
            "💡 Send your wallet address to link it."
        ),
        parse_mode="Markdown"
    )

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💬 Available Commands:\n\n"
        "/start - Start the bot\n"
        "/plans - View all plans\n"
        "/help - Show this help message\n\n"
        "You can also send your wallet address to link it to your account."
    )
    await update.message.reply_text(help_text)

# Handle wallet address message
async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet_address = update.message.text.strip()
    USER_WALLETS[user_id] = wallet_address
    await update.message.reply_text(
        f"✅ Wallet address linked successfully:\n`{wallet_address}`",
        parse_mode="Markdown"
    )

# Main
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    app.add_handler(MessageHandler(filters.COMMAND, help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.COMMAND, help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))

    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(handle_plan))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
