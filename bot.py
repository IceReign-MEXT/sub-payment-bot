# bot.py

import os
import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from solana.rpc.api import Client as SolanaClient
from web3 import Web3

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
INFURA_KEY = os.getenv("INFURA_KEY")

# Initialize Telegram bot
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Initialize Ethereum client
w3 = Web3(Web3.HTTPProvider(INFURA_KEY))

# Initialize Solana client
sol_client = SolanaClient("https://api.mainnet-beta.solana.com")


# ------------------------------
# Payment Verification Functions
# ------------------------------

async def check_eth_payment(address: str, expected_amount: float):
    try:
        balance = w3.eth.get_balance(address)
        return balance >= w3.to_wei(expected_amount, "ether")
    except Exception as e:
        print(f"[ERROR] ETH check failed: {e}")
        return False


async def check_solana_payment(address: str, expected_amount: float):
    try:
        balance = sol_client.get_balance(address)["result"]["value"]
        return balance >= int(expected_amount * 10**9)
    except Exception as e:
        print(f"[ERROR] Solana check failed: {e}")
        return False


# ------------------------------
# Telegram Command Handlers
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Pay to Activate", callback_data="pay")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! You must pay to activate this bot.\nClick below to pay:",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start the bot\n/help - Show commands\n/check - Check payment status"
    )


async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = context.user_data

    eth_address = user_data.get("eth_address")
    sol_address = user_data.get("sol_address")

    eth_paid = await check_eth_payment(eth_address, 0.01) if eth_address else False
    sol_paid = await check_solana_payment(sol_address, 0.01) if sol_address else False

    if eth_paid or sol_paid:
        await update.message.reply_text("Payment verified! Bot is now active for you.")
        await notify_owner(f"User {user_id} paid successfully.")
    else:
        await update.message.reply_text("Payment not found. Please pay first.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "pay":
        await query.edit_message_text(
            text=f"Please send payment to:\nETH: {SAFE_ETH_WALLET}\nSOL: {SAFE_SOL_WALLET}"
        )


# ------------------------------
# Owner Notifications
# ------------------------------

async def notify_owner(message: str):
    try:
        await app.bot.send_message(chat_id=OWNER_ID, text=message)
    except Exception as e:
        print(f"[ERROR] Failed to notify owner: {e}")


# ------------------------------
# Handlers Registration
# ------------------------------

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("check", check_payment))
app.add_handler(CallbackQueryHandler(button_handler))

# ------------------------------
# Main Entry
# ------------------------------

if __name__ == "__main__":
    print("Bot started...")
    app.run_polling()
