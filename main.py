import os
import requests
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    Updater,
    CallbackContext,
)

# Load environment variables from the .env file
load_dotenv()

# Configuration from .env file
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
DEPOSIT_WALLET_ADDRESS = "YOUR_MASTER_DEPOSIT_WALLET"  # Replace with the actual wallet where you receive funds
MIN_PAYMENT = float(os.getenv("MIN_PAYMENT", 0.01))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Set up FastAPI for webhook (if using)
app = FastAPI()

# Set up Telegram Bot
bot = Bot(BOT_TOKEN)

# Dummy database for user payments and verification status
# In a real app, this would be a database (like SQLite, PostGres, etc.)
user_payments = {}

def start_command(update: Update, context: CallbackContext) -> None:
    """Handles the /start command."""
    update.message.reply_text(
        "Hello! I am a payment verification bot. Send /getaddress to get your deposit address and verify your payment."
    )

def get_address_command(update: Update, context: CallbackContext) -> None:
    """Provides the user with a payment address and instructions."""
    user_id = update.effective_user.id
    # In a real app, you would generate a unique wallet address for each user
    # For this example, we use a single deposit address and rely on transaction verification
    update.message.reply_text(
        f"Please send at least {MIN_PAYMENT} SOL to the following address to activate your service:\n\n`{DEPOSIT_WALLET_ADDRESS}`\n\nAfter sending, use the /checkpayment command to verify your transaction.",
        parse_mode="Markdown",
    )

def check_payment_command(update: Update, context: CallbackContext) -> None:
    """Checks for the user's payment on the blockchain."""
    user_id = update.effective_user.id
    update.message.reply_text("Checking for your payment, this may take a moment...")

    # Call a function to scan the blockchain for a payment from this user
    if verify_payment(user_id):
        user_payments[user_id] = True
        update.message.reply_text("✅ Payment successfully verified! Your service is now active.")
    else:
        update.message.reply_text(
            "⏳ Payment not yet detected. Please wait a few moments and try again, or ensure you sent the correct amount to the correct address."
        )

def verify_payment(user_id) -> bool:
    """
    Scans the blockchain for a transaction from the user to the deposit address.
    This is a simplified example. A real implementation would use a robust
    blockchain library like `solders` or `anchor` to query the chain.
    """
    try:
        # Example API call to check transactions on Solana
        # A real implementation would need to track unique transactions
        # This is a dummy example
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getConfirmedSignaturesForAddress2",
            "params": [DEPOSIT_WALLET_ADDRESS, {"limit": 50}],
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(SOLANA_RPC_URL, data=json.dumps(payload), headers=headers)
        data = response.json()

        # Simplified logic: just check if any recent transaction was to our address
        # A real bot would need more complex logic to verify the *sender*
        # and the *amount* of a specific transaction.
        if data.get("result"):
            for tx in data["result"]:
                # This check is insufficient for production.
                # It would need to verify the `sender` and `amount`
                # (which aren't available in this specific API result)
                # It's better to use `get_transaction` on individual signatures
                pass
            return True # Assume success for the sake of the example
    except Exception as e:
        print(f"Error verifying payment: {e}")
        return False

    return False

def setup_bot():
    """Sets up and runs the Telegram bot."""
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("getaddress", get_address_command))
    dispatcher.add_handler(CommandHandler("checkpayment", check_payment_command))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    setup_bot()

# FastAPI setup (for webhooks, requires more complex setup)
# @app.post("/webhook")
# async def telegram_webhook(request: Request):
#     data = await request.json()
#     update = Update.de_json(data, bot)
#     setup_bot().dispatcher.process_update(update)
#     return {"ok": True}

