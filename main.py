import os
import logging
import asyncio
import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. CONFIGURATION ---
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_CHAT_ID")
ETH_WALLET = os.getenv("ETH_WALLET")

# Validation
if not API_TOKEN or not ADMIN_ID or not ETH_WALLET:
    print("❌ CRITICAL ERROR: Missing keys in .env file!")
    exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print("❌ ERROR: ADMIN_CHAT_ID in .env must be a number!")
    exit(1)

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
    buttons.append([InlineKeyboardButton(text="📞 Support", url="https://t.me/IceReign_MEXT")]) # Change to your username
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

    # Notify Admin
    admin_msg = (
        f"💰 **NEW PAYMENT CLAIM**\n\n"
        f"👤 User: {user.full_name} (@{user.username})\n"
        f"🆔 ID: `{user.id}`\n\n"
        "Check your wallet. If money received, send:\n"
        f"`/approve {user.id}`"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        await callback.message.edit_text("✅ **Request Received!**\n\nAdmin is verifying your transaction. You will receive a notification once approved.")
    except Exception as e:
        await callback.message.answer("⚠️ Error contacting admin. Please try again later.")

# --- 6. ADMIN COMMANDS ---
@dp.message(Command("approve"))
async def cmd_approve(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return # Ignore non-admins

    try:
        target_id = int(message.text.split()[1])
        await set_premium(target_id)

        # Notify User
        success_msg = (
            "🎉 **MEMBERSHIP APPROVED!**\n\n"
            "Your payment has been verified.\n"
            "Tap /start to access the content now."
        )
        await bot.send_message(target_id, success_msg, parse_mode="Markdown")
        await message.reply(f"✅ User {target_id} upgraded to PREMIUM.")

    except IndexError:
        await message.reply("❌ Use format: `/approve 123456`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@dp.callback_query(F.data == "get_content")
async def cb_content(callback: types.CallbackQuery):
    status = await get_user_status(callback.from_user.id)
    if status != "premium":
        await callback.answer("⛔ You are not Premium yet!", show_alert=True)
        return

    # --- REPLACE THE LINK BELOW WITH YOUR REAL PRODUCT ---
    secret_msg = (
        "🔓 **ACCESS GRANTED**\n\n"
        "Here is your private invite link:\n"
        "👉 [JOIN VIP CHANNEL NOW](https://t.me/+YOUR_SECRET_INVITE_LINK)\n\n"
        "Please do not share this link."
    )
    await callback.message.edit_text(secret_msg, parse_mode="Markdown", disable_web_page_preview=True)

# --- 7. RUNNER ---
async def main():
    await init_db()
    print("✅ Bot started! Press Ctrl+C to stop.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
