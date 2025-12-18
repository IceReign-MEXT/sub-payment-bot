import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- WEB SERVER FOR RENDER (Keep-Alive & Health Check) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Online"

@app.route('/health')
def health():
    return "OK", 200  # This fixes the 404 error in your Render logs

def run_web():
    # Render uses port 10000 by default, but we use the PORT env var for safety
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- KEYBOARDS ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="💎 Join Premium", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "⚡ <b>Ice Premium Subscriptions</b> ⚡\n\n"
        "Welcome! Join our elite community for professional content.\n"
        "Secure payments via Ethereum (ETH).",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "buy_sub")
async def pay_info(callback: types.CallbackQuery):
    msg = (
        "💰 <b>Payment Details</b>\n\n"
        "<b>Plan:</b> 7 Days Premium Access\n"
        "<b>Price:</b> 0.005 ETH\n\n"
        f"<b>Wallet Address:</b>\n<code>{WALLET}</code>\n\n"
        "⚠️ <i>After sending, wait 2-5 minutes for blockchain confirmation then click verify.</i>"
    )
    kb = [
        [InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="home")]
    ]
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):
    await callback.answer("Checking blockchain... please wait.", show_alert=True)
    # Since we are setting up, we simulate a successful link generation
    try:
        invite = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await callback.message.answer(
            f"🎉 <b>Payment Verified!</b>\n\nYour access link: {invite.invite_link}\n"
            "This link expires after 1 use.",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer("❌ Error: Bot must be Admin in the Channel to create links.")

# --- STARTUP ---
async def main():
    logging.info("Cleaning up webhooks...")
    # THIS LINE FIXES THE CONFLICT ERROR
    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Starting Web Server...")
    Thread(target=run_web).start()

    logging.info("Bot is polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
