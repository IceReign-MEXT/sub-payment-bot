import os
import logging
import asyncio
import asyncpg
import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# --- 1. CONFIGURATION ---
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_CHAT_ID")
ETH_WALLET = os.getenv("ETH_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
INVITE_LINK = os.getenv("INVITE_LINK")
PORT = int(os.getenv("PORT", 8080))

# Critical Check
required_vars = [API_TOKEN, ADMIN_ID, ETH_WALLET, ETHERSCAN_KEY, DATABASE_URL, INVITE_LINK]
if any(v is None for v in required_vars):
    print("❌ CRITICAL ERROR: Missing variables in .env file!")

try:
    ADMIN_ID = int(ADMIN_ID)
except:
    pass

# --- 2. SETUP ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
pool = None # Database Connection

class PaymentState(StatesGroup):
    waiting_for_tx = State()
    waiting_for_broadcast = State()

# --- 3. DATABASE ENGINE (Supabase/Postgres) ---
async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    status TEXT DEFAULT 'free',
                    tx_hash TEXT UNIQUE,
                    joined_at TIMESTAMP DEFAULT NOW()
                )
            """)
        print("✅ Connected to Cloud Database")
    except Exception as e:
        print(f"❌ Database Connection Error: {e}")

async def add_user(user_id, username):
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET username = $2
        """, user_id, username)

async def get_user_status(user_id):
    if not pool: return "free"
    async with pool.acquire() as conn:
        status = await conn.fetchval("SELECT status FROM users WHERE user_id = $1", user_id)
        return status if status else "free"

async def set_premium(user_id, tx_hash):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET status = 'premium', tx_hash = $1 WHERE user_id = $2", tx_hash, user_id)

async def check_tx_used(tx_hash):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT user_id FROM users WHERE tx_hash = $1", tx_hash)

async def get_all_users():
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id FROM users")

# --- 4. ETHERSCAN LOGIC ---
async def verify_eth_transaction(tx_hash):
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if "result" not in data or not data["result"]: return False, "❌ Transaction not found."

            tx = data["result"]
            if tx["to"].lower() != ETH_WALLET.lower(): return False, "❌ Wrong wallet address."

            value_eth = int(tx["value"], 16) / 10**18
            if value_eth < 0.001: return False, f"❌ Amount too low ({value_eth:.5f} ETH)."

            return True, "✅ Payment Verified."

# --- 5. MENUS ---
def main_menu(status):
    buttons = []
    if status == "premium":
        buttons.append([InlineKeyboardButton(text="🚀 ACCESS VIP CHANNEL", callback_data="get_content")])
    else:
        buttons.append([InlineKeyboardButton(text="💎 Buy Lifetime Access ($10)", callback_data="buy_sub")])

    buttons.append([InlineKeyboardButton(text="👤 Status", callback_data="profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Verify Transaction", callback_data="verify_tx")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="start")]
    ])

# --- 6. BOT HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username)
    status = await get_user_status(message.from_user.id)

    text = (
        f"👋 **Welcome, {message.from_user.first_name}!**\n\n"
        "Unlock exclusive signals and content via the **IceReign VIP**.\n\n"
        f"🔒 **Status:** {'✅ PREMIUM' if status == 'premium' else '❌ FREE'}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu(status))

@dp.callback_query(F.data == "start")
async def cb_home(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_start(callback.message)

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: types.CallbackQuery):
    status = await get_user_status(callback.from_user.id)
    await callback.answer(f"Your Status: {status.upper()}", show_alert=True)

@dp.callback_query(F.data == "buy_sub")
async def cb_buy(callback: types.CallbackQuery):
    text = (
        f"💳 **PAYMENT INSTRUCTIONS**\n\n"
        f"Send **$10 ETH** to:\n`{ETH_WALLET}`\n(Tap to copy)\n\n"
        "After sending, click **Verify Transaction** and paste your Hash."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=payment_menu())

@dp.callback_query(F.data == "verify_tx")
async def cb_verify(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 **Paste your Transaction Hash (TXID) now:**")
    await state.set_state(PaymentState.waiting_for_tx)

@dp.message(StateFilter(PaymentState.waiting_for_tx))
async def process_tx(message: types.Message, state: FSMContext):
    tx_hash = message.text.strip()
    msg = await message.reply("⏳ Checking blockchain...")

    if await check_tx_used(tx_hash):
        await msg.edit_text("❌ Error: Hash already used.")
        return

    try:
        is_valid, res_text = await verify_eth_transaction(tx_hash)
        if is_valid:
            await set_premium(message.from_user.id, tx_hash)
            await msg.edit_text("🎉 **PAYMENT APPROVED!**\n\nYou are now a VIP member.")
            await bot.send_message(ADMIN_ID, f"💰 **New Sale!**\nUser: @{message.from_user.username}\nHash: `{tx_hash}`")
            await message.answer("👇 Click below to join:", reply_markup=main_menu("premium"))
            await state.clear()
        else:
            await msg.edit_text(res_text)
    except Exception as e:
        print(e)
        await msg.edit_text("⚠️ API Error. Please try again later.")

@dp.callback_query(F.data == "get_content")
async def cb_content(callback: types.CallbackQuery):
    status = await get_user_status(callback.from_user.id)
    if status == "premium":
        await callback.message.edit_text(f"🔓 **VIP LINK:** [CLICK TO JOIN]({INVITE_LINK})", parse_mode="Markdown")
    else:
        await callback.answer("⛔ Payment Required", show_alert=True)

# --- 7. ADMIN BROADCAST ---
@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.reply("📢 Send the message you want to broadcast to all users:")
    await state.set_state(PaymentState.waiting_for_broadcast)

@dp.message(StateFilter(PaymentState.waiting_for_broadcast))
async def process_broadcast(message: types.Message, state: FSMContext):
    users = await get_all_users()
    count = 0
    for user in users:
        try:
            await bot.send_message(user['user_id'], message.text)
            count += 1
            await asyncio.sleep(0.1) # Anti-spam safety
        except:
            pass
    await message.reply(f"✅ Message sent to {count} users.")
    await state.clear()

# --- 8. WEB SERVER (For Render) ---
async def health(req): return web.Response(text="Bot is Alive")

async def main():
    await init_db()

    # Start Web Server
    app = web.Application()
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    print("✅ Bot and Web Server Started")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
