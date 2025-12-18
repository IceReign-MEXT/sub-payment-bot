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

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID")

init_db()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- WEB SERVER (RENDER STABILITY) ---
app = Flask('')
@app.route('/')
def home(): return "Ice System: Active"
@app.route('/health')
def health(): return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- FSM STATES ---
class PaymentStates(StatesGroup):
    waiting_for_wallet = State()

# --- BLOCKCHAIN VERIFIER ---
async def verify_eth_payment(user_wallet, amount_eth):
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={WALLET}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_KEY}"
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

# --- LIVE MONITORING (THE PROFESSIONAL READ) ---

@dp.channel_post()
async def monitor_channel_activity(message: types.Message):
    """Logs everything you post in your channel to your Admin DM"""
    log_text = (
        "📢 <b>Channel Post Detected</b>\n"
        f"<b>Source:</b> {message.chat.title}\n"
        "------------------\n"
        f"{message.text or '[Media Content]'}\n"
        "------------------\n"
        f"🕒 {datetime.now().strftime('%H:%M:%S')}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=log_text, parse_mode="HTML")

@dp.chat_member()
async def track_members(chat_member: ChatMemberUpdated):
    """Notifies you when people join or leave"""
    user = chat_member.from_user
    new_status = chat_member.new_chat_member.status

    if new_status == "member":
        status_text = "✅ <b>New Subscriber Joined!</b>"
    elif new_status in ["left", "kicked"]:
        status_text = "❌ <b>Subscriber Left</b>"
    else:
        return

    log_msg = (
        f"{status_text}\n"
        f"<b>User:</b> {user.first_name} (@{user.username})\n"
        f"<b>ID:</b> <code>{user.id}</code>"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=log_msg, parse_mode="HTML")

# --- USER HANDLERS ---

@dp.message(Command("start"))
async def start(message: types.Message):
    welcome = (
        f"👑 <b>Welcome to Ice Premium, {message.from_user.first_name}!</b>\n\n"
        "Unlock elite trading signals and exclusive insights.\n\n"
        "💳 <b>Rate:</b> 0.005 ETH / 7 Days"
    )
    kb = [
        [InlineKeyboardButton(text="💎 Purchase Subscription", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")]
    ]
    await message.answer(welcome, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "buy_sub")
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 <b>Wallet Registration</b>\n\nPlease send your ETH wallet address below:", parse_mode="HTML")
    await state.set_state(PaymentStates.waiting_for_wallet)

@dp.message(PaymentStates.waiting_for_wallet)
async def get_wallet(message: types.Message, state: FSMContext):
    wallet_address = message.text.strip()
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        await message.answer("❌ Invalid ETH address. Try again.")
        return

    await state.update_data(user_wallet=wallet_address)
    msg = (
        "💰 <b>Step 2: Payment</b>\n\n"
        f"Send: <code>0.005</code> ETH\n"
        f"To: <code>{WALLET}</code>\n\n"
        "Wait 2 minutes after sending then click verify."
    )
    kb = [[InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify_now")]]
    await message.answer(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify_now")
async def verify_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_wallet = data.get("user_wallet")

    await callback.answer("Searching Blockchain...", show_alert=False)
    if await verify_eth_payment(user_wallet, 0.005):
        add_subscription(callback.from_user.id, 7, "Weekly")
        invite = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await callback.message.answer(f"🎉 <b>Success!</b>\n\nAccess Link: {invite.invite_link}", parse_mode="HTML")

        # Admin Notification
        await bot.send_message(ADMIN_ID, f"💰 <b>REVENUE ALERT:</b> Received 0.005 ETH from @{callback.from_user.username}")
        await state.clear()
    else:
        await callback.message.answer("❌ <b>Payment Not Found.</b> Try again in 2 minutes.", parse_mode="HTML")

# --- STARTUP ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web).start()
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "channel_post", "chat_member"])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
