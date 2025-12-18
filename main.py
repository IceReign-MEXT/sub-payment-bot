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
from database import init_db, add_subscription, check_subscription
from flask import Flask
from threading import Thread

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID")
init_db()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Professional Sub Bot Online"
@app.route('/health')
def health(): return "OK", 200

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- STATES ---
class PaymentStates(StatesGroup):
    waiting_for_wallet = State()

# --- BLOCKCHAIN VERIFICATION ---
async def verify_eth_payment(user_wallet, amount_eth):
    """Checks Etherscan for a transaction from user_wallet to admin WALLET"""
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={WALLET}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get('status') == '1':
                for tx in data['result']:
                    # Check if sender matches, receiver matches, and value is correct (Wei conversion)
                    is_sender = tx['from'].lower() == user_wallet.lower()
                    value_eth = float(tx['value']) / 10**18
                    if is_sender and value_eth >= amount_eth:
                        # Ensure transaction happened in the last 24 hours
                        tx_time = datetime.fromtimestamp(int(tx['timeStamp']))
                        if datetime.now() - tx_time < timedelta(hours=24):
                            return True
            return False

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message):
    # Professional branding
    welcome = (
        f"👑 <b>Welcome to Ice Premium, {message.from_user.first_name}!</b>\n\n"
        "Unlock access to our exclusive high-signal channel.\n\n"
        "💳 <b>Current Price:</b> 0.005 ETH / 7 Days"
    )
    kb = [
        [InlineKeyboardButton(text="💎 Purchase Subscription", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")]
    ]
    await message.answer(welcome, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "buy_sub")
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    instruction = (
        "🔗 <b>Step 1: Register your Wallet</b>\n\n"
        "Please send your <b>Ethereum Wallet Address</b> below.\n"
        "I need this to verify your payment on the blockchain."
    )
    await callback.message.answer(instruction, parse_mode="HTML")
    await state.set_state(PaymentStates.waiting_for_wallet)

@dp.message(PaymentStates.waiting_for_wallet)
async def get_wallet(message: types.Message, state: FSMContext):
    wallet_address = message.text.strip()
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        await message.answer("❌ Invalid ETH address. Please send a valid address starting with 0x.")
        return

    await state.update_data(user_wallet=wallet_address)

    payment_msg = (
        "💰 <b>Step 2: Send Payment</b>\n\n"
        f"Amount: <code>0.005</code> ETH\n"
        f"To Address: <code>{WALLET}</code>\n\n"
        "⚠️ <b>Important:</b> Once sent, wait for 1 network confirmation (approx 2 mins) then click verify."
    )
    kb = [[InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify_now")]]
    await message.answer(payment_msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify_now")
async def verify_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_wallet = data.get("user_wallet")

    await callback.answer("Searching Blockchain... ⏳", show_alert=False)

    success = await verify_eth_payment(user_wallet, 0.005)

    if success:
        add_subscription(callback.from_user.id, 7, "Weekly Premium")
        invite = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await callback.message.answer(
            "🎉 <b>Payment Verified!</b>\n\n"
            f"Here is your exclusive link: {invite.invite_link}\n\n"
            "This link will only work for you.", parse_mode="HTML"
        )
        await state.clear()
    else:
        await callback.message.answer(
            "❌ <b>Transaction Not Found</b>\n\n"
            "We couldn't find a transaction for 0.005 ETH from your address yet.\n"
            "Please wait 2 minutes and try again."
        )

@dp.callback_query(F.data == "status")
async def check_my_status(callback: types.CallbackQuery):
    if check_subscription(callback.from_user.id):
        await callback.answer("✅ Your Premium access is ACTIVE.", show_alert=True)
    else:
        await callback.answer("❌ You do not have an active subscription.", show_alert=True)

# --- STARTUP ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
