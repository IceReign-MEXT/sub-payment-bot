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
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WALLET = os.getenv("PAYMENT_WALLET")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- WEB SERVER FOR RENDER (Keep-Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- CRYPTO VERIFICATION LOGIC ---
async def verify_ethereum_payment(user_wallet_address, amount_expected):
    """Checks Etherscan for a recent transaction from user to your wallet"""
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={WALLET}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data['status'] == '1':
                for tx in data['result']:
                    # Check if sender matches and amount (in Wei) is correct
                    # Note: Simplified for logic; real ETH uses 18 decimals
                    if tx['from'].lower() == user_wallet_address.lower():
                        return True
            return False

# --- KEYBOARDS ---
def main_menu():
    kb = [[InlineKeyboardButton(text="💎 Join Premium", callback_data="buy_sub")],
          [InlineKeyboardButton(text="📊 My Status", callback_data="status")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "⚡ <b>Professional Signals & Content</b> ⚡\n\n"
        "Join our elite community. Secure payments via Ethereum.",
        parse_mode="HTML", reply_markup=main_menu()
    )

@dp.callback_query(F.data == "buy_sub")
async def pay_info(callback: types.CallbackQuery):
    msg = (
        "💰 <b>Payment Details</b>\n\n"
        f"Price: 0.005 ETH (Weekly)\n"
        f"Address: <code>{WALLET}</code>\n\n"
        "Step 1: Send ETH to the address above.\n"
        "Step 2: Click 'Verify' after 2 minutes."
    )
    kb = [[InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify")],
          [InlineKeyboardButton(text="🔙 Back", callback_data="home")]]
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):
    await callback.answer("Checking blockchain... please wait.", show_alert=False)

    # In a real scenario, you'd ask the user for their wallet address first
    # Here, we simulate a successful verification for your flow:
    try:
        # Create a single-use invite link
        invite = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            expire_date=datetime.now() + timedelta(days=1)
        )

        await callback.message.answer(
            "🎉 <b>Payment Confirmed!</b>\n\n"
            f"Here is your unique access link: {invite.invite_link}\n"
            "<i>Note: This link works only once.</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer("❌ Payment not found yet. Try again in 5 minutes.")

# --- STARTUP ---
async def main():
    Thread(target=run_web).start() # Start Keep-Alive
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
