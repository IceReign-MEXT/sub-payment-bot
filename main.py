import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db, add_subscription, check_subscription
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# These are pulled from your Render Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID")

# Initialize Database
init_db()

# Initialize Bot and Dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- WEB SERVER FOR RENDER (Keep-Alive & Health Check) ---
app = Flask('')

@app.route('/')
def home():
    return "Ice Premium System: Online"

@app.route('/health')
def health():
    return "OK", 200

def run_web():
    # Render uses port 10000 by default
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- FSM STATES ---
class PaymentStates(StatesGroup):
    waiting_for_wallet = State()

# --- BLOCKCHAIN VERIFICATION LOGIC ---
async def verify_eth_payment(user_wallet, amount_eth):
    """
    Queries Etherscan to verify if a transaction exists
    from the user's wallet to your admin wallet.
    """
    url = (
        f"https://api.etherscan.io/api?module=account&action=txlist"
        f"&address={WALLET}&startblock=0&endblock=99999999"
        f"&sort=desc&apikey={ETHERSCAN_KEY}"
    )

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get('status') == '1':
                    for tx in data['result']:
                        # 1. Check if sender matches
                        is_sender = tx['from'].lower() == user_wallet.lower()
                        # 2. Check if amount matches (converted from Wei)
                        value_eth = float(tx['value']) / 10**18
                        # 3. Check if transaction is recent (within last 24 hours)
                        tx_time = datetime.fromtimestamp(int(tx['timeStamp']))
                        is_recent = datetime.now() - tx_time < timedelta(hours=24)

                        if is_sender and value_eth >= amount_eth and is_recent:
                            return True
                return False
        except Exception as e:
            logging.error(f"Blockchain Error: {e}")
            return False

# --- KEYBOARDS ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="💎 Purchase Premium", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📊 My Subscription Status", callback_data="status")],
        [InlineKeyboardButton(text="📞 Contact Support", url="https://t.me/MexRobert")] # Update your handle
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- BOT HANDLERS ---

@dp.message(Command("start"))
async def start(message: types.Message):
    welcome_text = (
        f"👑 <b>Welcome to Ice Premium, {message.from_user.first_name}!</b>\n\n"
        "Unlock access to high-accuracy trading signals and exclusive market insights.\n\n"
        "💳 <b>Current Rate:</b> 0.005 ETH / 7 Days\n\n"
        "Select an option below to begin:"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "buy_sub")
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    instruction = (
        "🔗 <b>Step 1: Wallet Registration</b>\n\n"
        "Please <b>send (type) your Ethereum Wallet Address</b> below.\n\n"
        "We use this to verify your payment on the blockchain."
    )
    await callback.message.answer(instruction, parse_mode="HTML")
    await state.set_state(PaymentStates.waiting_for_wallet)

@dp.message(PaymentStates.waiting_for_wallet)
async def get_wallet(message: types.Message, state: FSMContext):
    wallet_address = message.text.strip()

    # Validate ETH address length and format
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        await message.answer("❌ <b>Invalid Address</b>\n\nPlease send a valid ETH address (starting with 0x).", parse_mode="HTML")
        return

    await state.update_data(user_wallet=wallet_address)

    payment_msg = (
        "💰 <b>Step 2: Send Payment</b>\n\n"
        f"<b>Amount:</b> <code>0.005</code> ETH\n"
        f"<b>To Address:</b> <code>{WALLET}</code>\n\n"
        "⚠️ <b>Important:</b> Once sent, wait about 2 minutes for the network to confirm, then click the verify button below."
    )
    kb = [
        [InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify_now")],
        [InlineKeyboardButton(text="❌ Cancel Order", callback_data="cancel_action")]
    ]
    await message.answer(payment_msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify_now")
async def verify_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_wallet = data.get("user_wallet")

    if not user_wallet:
        await callback.message.answer("❌ Session expired. Please /start again.")
        return

    await callback.answer("Searching Blockchain... ⏳", show_alert=False)

    # Verification check
    is_valid = await verify_eth_payment(user_wallet, 0.005)

    if is_valid:
        # 1. Update Database
        add_subscription(callback.from_user.id, 7, "Weekly Premium")

        # 2. Generate One-Time Invite Link
        try:
            invite = await bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
                name=f"Sub: {callback.from_user.id}"
            )

            await callback.message.answer(
                "🎉 <b>Payment Verified!</b>\n\n"
                "Welcome to the Ice Premium family. Your access link is below:\n\n"
                f"{invite.invite_link}\n\n"
                "<i>Note: This link is for 1-time use only.</i>",
                parse_mode="HTML"
            )
            await state.clear()
        except Exception as e:
            await callback.message.answer("⚠️ Payment verified, but I couldn't create an invite link. Contact Admin.")
            logging.error(f"Invite Error: {e}")
    else:
        await callback.message.answer(
            "❌ <b>Transaction Not Found</b>\n\n"
            "We haven't detected your 0.005 ETH payment yet.\n\n"
            "1. Ensure you sent the correct amount.\n"
            "2. Ensure you used the wallet address you registered.\n"
            "3. Wait 2 minutes for blockchain sync and try again.",
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "status")
async def check_status(callback: types.CallbackQuery):
    is_active = check_subscription(callback.from_user.id)
    if is_active:
        await callback.answer("✅ Your Premium Access is currently ACTIVE!", show_alert=True)
    else:
        await callback.answer("❌ You do not have an active subscription.", show_alert=True)

@dp.callback_query(F.data == "cancel_action")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Payment cancelled. Use /start to try again.")

# --- STARTUP LOGIC ---
async def main():
    # Fix for the 'Conflict' error: Delete existing webhooks
    logging.info("Clearing Webhooks...")
    await bot.delete_webhook(drop_pending_updates=True)

    # Start the Flask server in a separate thread for Render
    logging.info("Starting Keep-Alive server...")
    Thread(target=run_web).start()

    # Start Polling
    logging.info("Bot is now Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
