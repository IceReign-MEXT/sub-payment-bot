import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db, add_subscription, check_subscription
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- FSM STATES ---
class PaymentStates(StatesGroup):
    waiting_for_wallet = State()

# --- BLOCKCHAIN VERIFICATION LOGIC ---
async def verify_eth_payment(user_wallet, amount_eth):
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
                        is_sender = tx['from'].lower() == user_wallet.lower()
                        value_eth = float(tx['value']) / 10**18
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
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")],
        [InlineKeyboardButton(text="📞 Support", url="https://t.me/MexRobert")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- BOT COMMAND HANDLERS ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome = (
        f"👑 <b>Welcome to Ice Premium, {message.from_user.first_name}!</b>\n\n"
        "Unlock access to our exclusive high-signal channel.\n\n"
        "💳 <b>Rate:</b> 0.005 ETH / 7 Days\n\n"
        "Click the button below to join the winners."
    )
    await message.answer(welcome, parse_mode="HTML", reply_markup=main_menu())

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    is_active = check_subscription(message.from_user.id)
    if is_active:
        await message.answer("✅ <b>Your Premium Access is ACTIVE!</b>", parse_mode="HTML")
    else:
        await message.answer("❌ <b>No Active Subscription.</b>\nUse /start to join.", parse_mode="HTML")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "💡 <b>How to join Ice Premium:</b>\n\n"
        "1️⃣ Click 'Purchase Premium'\n"
        "2️⃣ Send your ETH wallet address to register\n"
        "3️⃣ Transfer 0.005 ETH to the admin wallet\n"
        "4️⃣ Click 'Verify' to get your instant link"
    )
    await message.answer(help_text, parse_mode="HTML")

# --- MONITORING HANDLERS (Professional Read) ---

@dp.channel_post()
async def monitor_channel(message: types.Message):
    """Logs everything you post in your channel to your Admin DM"""
    log = f"📢 <b>Post in {message.chat.title}:</b>\n\n{message.text or '[Media Content]'}"
    await bot.send_message(chat_id=ADMIN_ID, text=log, parse_mode="HTML")

@dp.chat_member()
async def track_members(chat_member: ChatMemberUpdated):
    """Notifies you when people join or leave your channel"""
    user = chat_member.from_user
    new_status = chat_member.new_chat_member.status
    if new_status == "member":
        msg = f"✅ <b>New Subscriber:</b> {user.first_name} (@{user.username})"
    elif new_status in ["left", "kicked"]:
        msg = f"❌ <b>Member Left:</b> {user.first_name} (@{user.username})"
    else: return
    await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="HTML")

# --- PAYMENT FLOW HANDLERS ---

@dp.callback_query(F.data == "buy_sub")
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 <b>Registration</b>\n\nPlease send your <b>ETH Wallet Address</b> below:", parse_mode="HTML")
    await state.set_state(PaymentStates.waiting_for_wallet)

@dp.message(PaymentStates.waiting_for_wallet)
async def get_wallet(message: types.Message, state: FSMContext):
    wallet = message.text.strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        await message.answer("❌ Invalid ETH address. Please try again.")
        return
    await state.update_data(user_wallet=wallet)
    msg = (
        "💰 <b>Payment Required</b>\n\n"
        f"Amount: <code>0.005</code> ETH\n"
        f"To: <code>{WALLET}</code>\n\n"
        "Wait 2 minutes after sending, then click verify."
    )
    kb = [[InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify_now")]]
    await message.answer(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify_now")
async def verify_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_wallet = data.get("user_wallet")
    await callback.answer("Searching Blockchain... ⏳")

    if await verify_eth_payment(user_wallet, 0.005):
        add_subscription(callback.from_user.id, 7, "Weekly")
        invite = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await callback.message.answer(f"🎉 <b>Verified!</b>\n\nAccess Link: {invite.invite_link}", parse_mode="HTML")
        await bot.send_message(ADMIN_ID, f"💰 <b>SALE:</b> 0.005 ETH from @{callback.from_user.username}")
        await state.clear()
    else:
        await callback.message.answer("❌ <b>Payment not found yet.</b> Try again in 2 minutes.", parse_mode="HTML")

@dp.callback_query(F.data == "status")
async def check_my_status(callback: types.CallbackQuery):
    is_active = check_subscription(callback.from_user.id)
    status = "✅ ACTIVE" if is_active else "❌ INACTIVE"
    await callback.answer(f"Subscription Status: {status}", show_alert=True)

# --- STARTUP ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web).start()
    print("Bot is starting...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "channel_post", "chat_member"])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
