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
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
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

if __name__ == "__main__":
    main()
