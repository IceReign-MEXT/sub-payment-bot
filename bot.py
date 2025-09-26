<<<<<<< HEAD
import os
import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from web3 import Web3
from solana.rpc.api import Client as SolanaClient

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("OWNER_ID"))
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
INFURA_KEY = os.getenv("INFURA_KEY")

# HTTP request with timeout
request = HTTPXRequest(connect_timeout=30, read_timeout=30, write_timeout=30)

# Ethereum and Solana clients
w3 = Web3(Web3.HTTPProvider(INFURA_KEY))
sol_client = SolanaClient("https://api.mainnet-beta.solana.com")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Subscription plans
PLANS = {
    "Daily": {"price": 7, "duration": 1, "currency": "ETH"},
    "Weekly": {"price": 15, "duration": 7, "currency": "ETH"},
    "Monthly": {"price": 100, "duration": 30, "currency": "ETH"},
    "Yearly": {"price": 1200, "duration": 365, "currency": "ETH"},
    "Lifetime": {"price": 1600, "duration": "Lifetime", "currency": "ETH"},
}

# Helper functions
def verify_eth_payment(amount_eth):
    balance = w3.eth.get_balance(SAFE_ETH_WALLET)
    balance_eth = w3.from_wei(balance, "ether")
    return balance_eth >= amount_eth

def verify_sol_payment(amount_sol):
    resp = sol_client.get_balance(SAFE_SOL_WALLET)
    balance_lamports = resp["result"]["value"]
    balance_sol = balance_lamports / 10**9
    return balance_sol >= amount_sol

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{plan} – ${details['price']}", callback_data=plan)]
        for plan, details in PLANS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to IceSub Bot!\n\nChoose your subscription plan below:",
        reply_markup=reply_markup
    )

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Help Menu\n\n"
        "/start - Begin and choose a plan\n"
        "/plans - View subscription options\n"
        "/wallet <address> - Optional: Set your wallet\n"
        "/help - Show this help message"
    )

# /plans command
async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for plan, details in PLANS.items():
        duration_text = f"{details['duration']} days" if isinstance(details['duration'], int) else details['duration']
        wallet = SAFE_ETH_WALLET if details['currency'] == "ETH" else SAFE_SOL_WALLET
        message = (
            f"📌 {plan} Plan\n"
            f"💵 Price: ${details['price']}\n"
            f"⏳ Duration: {duration_text}\n"
            f"💰 Wallet for payment:\n{wallet}"
        )
        await update.message.reply_text(message)

# /wallet command
async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please send your wallet like this:\n/wallet 0xYourWalletAddress")
        return
    user_wallet = context.args[0]
    await update.message.reply_text(f"✅ Wallet saved: {user_wallet}")

# Handle subscription button click
=======
import asyncio
import time
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

from config import BOT_TOKEN, OWNER_ID
from database import init_db, add_pending_payment_request, get_pending_payment_requests, mark_payment_processed, add_subscription, get_latest_subscription
from payments import get_crypto_price, verify_eth_payment, verify_sol_payment
from subscriptions import PLANS

# --- Telegram Bot Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    await update.message.reply_text("💎 Welcome to the Crypto Subscription Bot! Use /plans to see available subscriptions.")

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /plans command to show available subscription plans."""
    keyboard = []
    for k, v in PLANS.items():
        keyboard.append([InlineKeyboardButton(f"{k} - ${v['price']}", callback_data=f"plan:{k}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💎 *Choose a subscription plan:*", 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )

>>>>>>> origin/main
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button clicks (e.g., plan selection)."""
    query = update.callback_query
<<<<<<< HEAD
    await query.answer()
    plan_name = query.data
    await handle_subscription(update, context, plan_name)

# Handle subscription logic
async def handle_subscription(update, context, plan_name):
    details = PLANS.get(plan_name)
    if not details:
        await update.callback_query.message.reply_text("❌ Invalid plan selected.")
        return

    currency = details['currency']
    price = details['price']
    duration = details['duration']
    wallet = SAFE_ETH_WALLET if currency == "ETH" else SAFE_SOL_WALLET

    await update.callback_query.message.reply_text(
        f"📌 You selected {plan_name} Plan.\n"
        f"💵 Price: ${price}\n"
        f"⏳ Duration: {duration}\n\n"
        f"✅ Send payment to this wallet:\n{wallet}"
    )

    # Notify admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"User @{update.effective_user.username} selected {plan_name} Plan. Waiting for payment..."
    )

    # Check payment
    for _ in range(20):
        paid = verify_eth_payment(price) if currency == "ETH" else verify_sol_payment(price)
        if paid:
            await update.callback_query.message.reply_text("✅ Payment received! Subscription activated.")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ User @{update.effective_user.username} completed payment for {plan_name} Plan."
            )
            return
        await asyncio.sleep(15)

    await update.callback_query.message.reply_text("❌ Payment not received. Please try again.")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("plans", plans_command))
    app.add_handler(CommandHandler("wallet", wallet_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.bot_data['admin_id'] = ADMIN_ID

    logger.info("🤖 Bot started...")
    app.run_polling()
=======
    await query.answer() # Acknowledge the callback query

    if query.data.startswith("plan:"):
        plan_name = query.data.split(":")[1]
        
        if plan_name not in PLANS:
            await query.message.reply_text("Invalid plan selected. Please try again.")
            return

        plan_details = PLANS[plan_name]
        usd_price = plan_details["price"]

        # Fetch current crypto prices
        eth_price = get_crypto_price("ETH")
        sol_price = get_crypto_price("SOL")

        if not eth_price or not sol_price:
            await query.message.reply_text("❌ Failed to fetch crypto prices. Please try again later.")
            return

        expected_eth_amount = round(usd_price / eth_price, 6)
        expected_sol_amount = round(usd_price / sol_price, 6)

        # Store pending payment requests in the database
        # NOTE: In a production bot, each payment request should ideally correspond to a unique, temporary wallet address
        # or a unique invoice ID generated by a payment gateway to ensure proper tracking and avoid sending to a shared address.
        # For simplicity here, we direct to the SAFE_ wallets, but this is a security risk for payment tracking in real apps.
        add_pending_payment_request(query.from_user.id, plan_name, "ETH", expected_eth_amount)
        add_pending_payment_request(query.from_user.id, plan_name, "SOL", expected_sol_amount)

        # Reply with payment instructions
        msg = (
            f"💰 *Payment Instructions for {plan_name} Plan*\n\n"
            f"Price: ${usd_price}\n\n"
            f"🔹 **Ethereum (ETH):**\n"
            f"Amount: `{expected_eth_amount}` ETH\n"
            f"Address: `{os.getenv('SAFE_ETH_WALLET')}`\n\n"
            f"🔹 **Solana (SOL):**\n"
            f"Amount: `{expected_sol_amount}` SOL\n"
            f"Address: `{os.getenv('SAFE_SOL_WALLET')}`\n\n"
            f"Once you send the payment, a background process will verify it automatically.\n"
            f"You will receive a confirmation message shortly after your payment is detected and confirmed on the blockchain."
            f"\n\n*Please ensure you send the exact crypto amount calculated.*"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

async def my_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the user their current subscription status."""
    user_id = update.effective_user.id
    subscription = get_latest_subscription(user_id)

    if subscription:
        expires_dt = datetime.fromtimestamp(subscription["expires_ts"])
        time_left = expires_dt - datetime.now()
        await update.message.reply_text(
            f"🌟 Your current plan: *{subscription['plan']}*\n"
            f"Expires on: `{expires_dt.strftime('%Y-%m-%d %H:%M:%S WAT')}`\n"
            f"Time remaining: `{time_left.days}` days, `{time_left.seconds // 3600}` hours",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("You don't have an active subscription. Use /plans to subscribe!")

# --- Background Task ---
async def check_payments_periodically(context: ContextTypes.DEFAULT_TYPE):
    """Background task to check for pending payments and update subscriptions."""
    pending_payments = get_pending_payment_requests()
    
    for payment in pending_payments:
        telegram_id = int(payment["telegram_id"])
        plan_name = payment["plan"]
        expected_amount = payment["expected_amount"]
        payment_chain = payment["chain"]
        
        is_paid = False
        tx_hash_found = None # Placeholder for a found transaction hash/signature

        # In a real bot, you'd have a mechanism to get the tx_hash/signature.
        # This could be from:
        # 1. User providing it (less reliable)
        # 2. Monitoring incoming transactions to the SAFE_WALLET (requires complex blockchain indexing)
        # For this example, let's assume we can somehow retrieve it.
        # For a full implementation, you would need to run blockchain scanners or use payment gateway webhooks.
        # For demonstration purposes, we will simulate finding a transaction.

        # Example: Mocking a transaction hash and verification
        # You'd replace this with actual blockchain monitoring and verification logic
        mock_tx_hash = "0xmocktransactionhash" + str(payment["id"]) # Just a placeholder
        
        if payment_chain == "ETH":
            # For demonstration, assume transaction is verified after some time
            # In real life: is_paid = await verify_eth_payment(actual_tx_hash, expected_amount)
            # You would need the actual_tx_hash for this to work.
            is_paid = True # Simulate success for demo
            tx_hash_found = mock_tx_hash 
        elif payment_chain == "SOL":
            # For demonstration, assume transaction is verified after some time
            # In real life: is_paid = await verify_sol_payment(actual_tx_signature, expected_amount)
            # You would need the actual_tx_signature for this to work.
            is_paid = True # Simulate success for demo
            tx_hash_found = mock_tx_hash

        if is_paid:
            mark_payment_processed(payment["id"], tx_hash=tx_hash_found)
            
            plan_details = PLANS[plan_name]
            duration_days = plan_details["duration"]
            
            start_ts = int(time.time())
            if duration_days is not None:
                expires_ts = start_ts + duration_days * 86400 # 86400 seconds in a day
            else: # Lifetime plan
                expires_ts = start_ts + 365 * 86400 * 100 # Effectively 100 years

            add_subscription(telegram_id, plan_name, start_ts, expires_ts)
            
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"✅ Payment for *{plan_name}* confirmed! Your subscription is now active.",
                parse_mode="Markdown"
            )
            print(f"💰 Confirmed payment for user {telegram_id}, plan {plan_name}.")

        # Introduce a small delay to avoid rate limiting or excessive processing
        await asyncio.sleep(0.5)

# --- Main Application Setup ---
def main():
    """Starts the bot."""
    init_db() # Initialize the database

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("plans", plans_command))
    application.add_handler(CommandHandler("mysubscription", my_subscription_command))
    
    # Register callback query handler for inline keyboard buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    # Schedule the background payment checker job to run every 60 seconds
    application.job_queue.run_repeating(check_payments_periodically, interval=60)
    
    print("🚀 Bot is polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
>>>>>>> origin/main

if __name__ == "__main__":
    main()

