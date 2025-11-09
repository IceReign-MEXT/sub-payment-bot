import os
import sqlite3
from datetime import datetime, timedelta
import asyncio
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# --- 1. CONFIGURATION AND INITIALIZATION ---
load_dotenv()

# Configuration from your .env file
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DB_FILE = 'subscriptions.db'

# 💰 UPGRADED SUBSCRIPTION PRICE (99 Stars)
PRICE_STARS = 99
SUBSCRIPTION_DAYS = 30
CURRENCY_CODE = "XTR" # Telegram Stars

def init_db():
    """Initializes the SQLite database for subscriptions and grants admin access."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            expiry_date TEXT,
            payment_id TEXT
        )
    """)
    # Grant the test admin a subscription for 30 days
    update_subscription(ADMIN_ID, days=30)
    print(f"Database initialized. Admin {ADMIN_ID} granted 30-day access.")
    conn.close()

def update_subscription(user_id: int, days: int, payment_id: str = None):
    """Extends or creates a subscription for the user, returning the new expiry date."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check current expiry date
    cursor.execute("SELECT expiry_date FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        current_expiry = datetime.fromisoformat(row[0])
        # Extend from the current expiry if it's in the future, otherwise start from now.
        start_date = max(datetime.now(), current_expiry)
    else:
        start_date = datetime.now()

    new_expiry = start_date + timedelta(days=days)
    new_expiry_str = new_expiry.isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO subscriptions (user_id, expiry_date, payment_id) 
        VALUES (?, ?, ?)
    """, (user_id, new_expiry_str, payment_id))

    conn.commit()
    conn.close()
    return new_expiry_str

def is_subscribed(user_id):
    """Checks if the user has an active subscription."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        expiry_date = datetime.fromisoformat(row[0])
        return expiry_date > datetime.now()
    return False

# --- 2. COMMAND HANDLERS (THE BUSINESS LOGIC) ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and prompts for subscription."""
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name

    if is_subscribed(user_id):
        await update.message.reply_text(
            f"Welcome back, {first_name}! Your **Secure Wallet Access** is currently **ACTIVE**.\n\n"
            "Use /premium for your features. Your assets are monitored.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"Welcome, {first_name}! This is the **Chino Secure Wallet Bot**.\n\n"
            "To unlock advanced wallet management and multi-chain security monitoring, please use the /buy command.",
        )

async def premium_feature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The protected feature access."""
    user_id = update.effective_user.id

    if is_subscribed(user_id):
        await update.message.reply_text(
            "✨ **ACCESS GRANTED:** Welcome to your Premium Wallet Dashboard. All advanced Solana and EVM tools are now unlocked.\n"
            "Monitor your linked wallets and execute private operations here.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🔒 **ACCESS DENIED:** You need an active subscription to use this feature.\n\n"
            f"Unlock Premium Access for only **{PRICE_STARS} Stars/30 days**.\nUse /buy to subscribe now.",
            parse_mode='Markdown'
        )

# --- 3. PAYMENT HANDLERS (THE MONETIZATION LOGIC) ---

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a Telegram Stars Invoice to the user."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if is_subscribed(user_id):
        await update.message.reply_text(
            "✨ You are already a premium user! No need to buy again right now. Enjoy your secured access."
        )
        return

    title = f"{SUBSCRIPTION_DAYS}-Day Premium Wallet Access"
    description = f"Unlock advanced security monitoring and tools for {SUBSCRIPTION_DAYS} days."

    # LabeledPrice is in the smallest unit. For Stars, this is 1:1.
    prices = [LabeledPrice(label=title, amount=PRICE_STARS)]

    # Internal payload for tracking the user and the plan
    payload = f"subscription_month_{user_id}_{datetime.now().timestamp()}"

    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="", # Empty string for standard XTR payments
            currency=CURRENCY_CODE,
            prices=prices,
            need_name=False,
            is_flexible=False,
            start_parameter="start_param",
        )
    except Exception as e:
        print(f"Error sending invoice: {e}")
        await update.message.reply_text("🚨 **PAYMENT ERROR:** Sorry, a problem occurred while generating the payment invoice. Please try again later.", parse_mode='Markdown')

async def pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers the Pre-Checkout Query (PCQ) sent by Telegram to confirm the invoice details."""
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles successful payments and grants access."""
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment

    # 1. EXTEND SUBSCRIPTION (The core business logic)
    new_expiry_str = update_subscription(
        user_id,
        days=SUBSCRIPTION_DAYS,
        payment_id=payment_info.telegram_payment_charge_id
    )

    # 2. NOTIFY USER
    await update.message.reply_text(
        f"👑 **ACCESS GRANTED!** Your {SUBSCRIPTION_DAYS}-day Premium Access has been activated.\n\n"
        f"Thank you for your {payment_info.total_amount} {payment_info.currency} payment. Your access expires on {new_expiry_str.split('T')[0]}.",
        parse_mode='Markdown',
        disable_notification=True
    )

# --- 4. MAIN EXECUTION (Webhook Mode for Hosting) ---

# We define the application instance globally. This is the 'application'
# object that Gunicorn/Uvicorn needs to find when running 'main:application'.
init_db()

application = Application.builder().token(BOT_TOKEN).build()

# 1. Add Handlers
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("premium", premium_feature))
application.add_handler(CommandHandler("buy", buy_subscription))

# 2. Payment Webhook Handlers
application.add_handler(PreCheckoutQueryHandler(pre_checkout_query))
application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

if __name__ == '__main__':
    # This block is used for local debugging but is ignored by Gunicorn/Uvicorn
    # If running locally, you must use polling to test:
    # application.run_polling(poll_interval=1.0)
    print("Application built. Ready to be launched by Gunicorn/Uvicorn on the host.")

