import os
import logging
import asyncio
import aiosqlite
from aiohttp import web # We use this to create the fake website
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. CONFIGURATION ---
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_CHAT_ID")
ETH_WALLET = os.getenv("ETH_WALLET")
PORT = int(os.getenv("PORT", 8080)) # Render gives us a PORT, we must use it

# Validation
if not API_TOKEN or not ADMIN_ID or not ETH_WALLET:
    print("❌ CRITICAL ERROR: Missing keys in .env file!")
    # We don't exit here so the web server can still start and show errors

try:
    ADMIN_ID = int(ADMIN_ID)
except:
    pass

# --- 2. SETUP ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
DB_NAME = "subscriptions.db"

# --- 3. DATABASE ENGINE ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                status TEXT DEFAULT 'free',
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

async def get_user_status(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else "free"

async def set_premium(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET status = 'premium' WHERE user_id = ?", (user_id,))
        await db.commit()

# --- 4. MENUS ---
def main_menu(status):
    buttons = []
    if status == "premium":
        buttons.append([InlineKeyboardButton(text="🚀 ACCESS PREMIUM CHANNEL", callback_data="get_content")])
    else:
        buttons.append([InlineKeyboardButton(text="💎 Buy Lifetime Access ($10)", callback_data="buy_sub")])

    buttons.append([InlineKeyboardButton(text="👤 My Account", callback_data="profile")])
    buttons.append([InlineKeyboardButton(text="📞 Support", url="https://t.me/IceReign_MEXT")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I Have Sent Payment", callback_data="confirm_payment")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="start")]
    ])

# --- 5. BOT LOGIC ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username)
    status = await get_user_status(message.from_user.id)

    welcome_text = (
        f"👋 **Welcome, {message.from_user.first_name}!**\n\n"
        "I am the official gateway to the **Exclusive VIP Community**.\n\n"
        "🔒 **Status:** " + ("✅ PREMIUM MEMBER" if status == "premium" else "❌ FREE USER")
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu(status))

@dp.callback_query(F.data == "start")
async def cb_home(callback: types.CallbackQuery):
    await cmd_start(callback.message)

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: types.CallbackQuery):
    status = await get_user_status(callback.from_user.id)
    msg = f"🆔 **ID:** `{callback.from_user.id}`\n👤 **User:** @{callback.from_user.username}\n💎 **Plan:** {status.upper()}"
    await callback.answer(msg, show_alert=True)

@dp.callback_query(F.data == "buy_sub")
async def cb_buy(callback: types.CallbackQuery):
    text = (
        "💳 **PAYMENT INSTRUCTIONS**\n\n"
        "Send **$10 USD** in ETH (Ethereum) to this address:\n\n"
        f"`{ETH_WALLET}`\n\n"
        "⚠️ **IMPORTANT:**\n"
        "1. Copy the address by tapping it.\n"
        "2. Make the transfer from your wallet.\n"
        "3. Click the 'I Have Sent Payment' button below."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=payment_menu())

@dp.callback_query(F.data == "confirm_payment")
async def cb_confirm(callback: types.CallbackQuery):
    user = callback.from_user
    admin_msg = (
        f"💰 **NEW PAYMENT CLAIM**\n\n"
        f"👤 User: {user.full_name} (@{user.username})\n"
        f"🆔 ID: `{user.id}`\n\n"
        "Check your wallet. If money received, send:\n"
        f"`/approve {user.id}`"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        await callback.message.edit_text("✅ **Request Received!**\n\nAdmin is verifying your transaction.")
    except Exception as e:
        await callback.message.answer("⚠️ Error contacting admin.")

@dp.message(Command("approve"))
async def cmd_approve(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        await set_premium(target_id)
        await bot.send_message(target_id, "🎉 **MEMBERSHIP APPROVED!**\n\nTap /start to access content.")
        await message.reply(f"✅ User {target_id} upgraded.")
    except:
        await message.reply("❌ Usage: `/approve 123456`")

@dp.callback_query(F.data == "get_content")
async def cb_content(callback: types.CallbackQuery):
    status = await get_user_status(callback.from_user.id)
    if status != "premium":
        await callback.answer("⛔ You are not Premium yet!", show_alert=True)
        return
    await callback.message.edit_text("🔓 **ACCESS GRANTED**\n\n👉 [JOIN VIP CHANNEL](https://t.me/+YOUR_SECRET_INVITE_LINK)", parse_mode="Markdown", disable_web_page_preview=True)

# --- 6. THE FAKE WEB SERVER (FOR RENDER FREE TIER) ---
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Web Server started on port {PORT}")

# --- 7. MAIN RUNNER ---
async def main():
    await init_db()
    # Start the fake website first
    await start_web_server()
    # Then start the bot
    print("✅ Bot polling started...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
