import asyncio
import os
from datetime import datetime, timedelta

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

print(f"Loaded token: {TOKEN[:10]}...{TOKEN[-10:]}")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET", "").lower().strip()
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY", "").strip()
PREMIUM_CHANNEL_ID = int(os.getenv("PREMIUM_CHANNEL_ID", "0"))
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID", "0"))

MONTHLY_ETH = 0.0033
LIFETIME_ETH = 0.0167

# High timeouts for reliability
request = HTTPXRequest(connect_timeout=60, read_timeout=60, pool_timeout=60, write_timeout=60)

# Build the application
app = Application.builder().token(TOKEN).request(request).build()
bot = app.bot

api = FastAPI()

# In-memory storage
subscriptions = {}
payments = {}

async def record_payment(tx_hash: str, user_id: int, value_eth: float):
    payments[tx_hash.lower()] = {"user_id": user_id, "value": value_eth}

async def activate(user_id: int, lifetime: bool = False):
    expiry = datetime(2099, 12, 31) if lifetime else (datetime.now() + timedelta(days=30))
    subscriptions[user_id] = expiry.timestamp()
    try:
        if PREMIUM_CHANNEL_ID != 0:
            await bot.unban_chat_member(PREMIUM_CHANNEL_ID, user_id)
        if PREMIUM_GROUP_ID != 0:
            await bot.unban_chat_member(PREMIUM_GROUP_ID, user_id)
    except Exception as e:
        print(f"Error granting access: {e}")

async def cleanup_task():
    while True:
        now = datetime.now().timestamp()
        expired = [uid for uid, exp in subscriptions.items() if exp < now]
        for uid in expired:
            try:
                if PREMIUM_CHANNEL_ID != 0:
                    await bot.ban_chat_member(PREMIUM_CHANNEL_ID, uid)
                if PREMIUM_GROUP_ID != 0:
                    await bot.ban_chat_member(PREMIUM_GROUP_ID, uid)
            except Exception as e:
                print(f"Error removing access: {e}")
            del subscriptions[uid]
        await asyncio.sleep(3600)  # hourly

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Welcome to ICE GODS ICE DEVILS Premium 🔥\n\n"
        "Use /plans to see subscription options\n"
        "/subscribe - get payment wallet\n"
        "/status - check your access"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 PREMIUM PLANS 💎\n\n"
        f"📅 Monthly: {MONTHLY_ETH} ETH (~$10)\n"
        f"👑 Lifetime: {LIFETIME_ETH} ETH (~$50)\n\n"
        "Use /subscribe to proceed"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not PAYMENT_WALLET:
        await update.message.reply_text("Payment wallet not configured.")
        return
    await update.message.reply_text(
        f"💰 Send ETH to this address:\n\n`{PAYMENT_WALLET}`\n\n"
        f"Monthly: exactly {MONTHLY_ETH} ETH\n"
        f"Lifetime: {LIFETIME_ETH} ETH or more\n\n"
        "After sending, use /paid <transaction_hash>",
        parse_mode=ParseMode.MARKDOWN
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in subscriptions:
        expiry = datetime.fromtimestamp(subscriptions[user_id])
        if expiry.year > 2050:
            await update.message.reply_text("👑 You have LIFETIME access!")
        else:
            await update.message.reply_text(f"📅 Access until: {expiry.strftime('%Y-%m-%d')}")
    else:
        await update.message.reply_text("❌ No active subscription. Use /plans")

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /paid <tx_hash>")
        return
    tx = context.args[0].strip().lower()
    if payments.get(tx):
        await update.message.reply_text("This transaction was already processed.")
        return

    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx}&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=60) as resp:
            data = await resp.json()

    if data.get("result") is None:
        await update.message.reply_text("Transaction not found or still pending.")
        return

    tx_data = data["result"]
    to_addr = tx_data.get("to", "").lower()
    value_wei = int(tx_data["value"], 16)
    value_eth = value_wei / 10**18

    if to_addr != PAYMENT_WALLET:
        await update.message.reply_text("Wrong recipient address.")
        return

    user_id = update.message.from_user.id
    await record_payment(tx, user_id, value_eth)

    if value_eth >= LIFETIME_ETH:
        await activate(user_id, lifetime=True)
        await update.message.reply_text("👑 LIFETIME access granted! Welcome to the gods 🔥")
    elif value_eth >= MONTHLY_ETH:
        await activate(user_id, lifetime=False)
        await update.message.reply_text("📅 Monthly access granted! Enjoy the premium 🚀")
    else:
        await update.message.reply_text(f"Amount too low. Sent {value_eth} ETH, need at least {MONTHLY_ETH} ETH.")

# Add handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("plans", plans))
app.add_handler(CommandHandler("subscribe", subscribe))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("paid", paid))

# Webhook endpoint with robust error handling
@api.post("/webhook")
async def webhook(req: Request):
    try:
        json_data = await req.json()
        print(f"Received update: {json_data}")
        update = Update.de_json(json_data, bot)
        if update is None:
            print("Invalid update - None after de_json")
            return {"ok": True}
        await app.process_update(update)
        return {"ok": True}
    except Exception as e:
        print(f"Webhook processing error: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": True}, 200

@api.get("/health")
def health():
    return {"status": "ok"}

# Startup
if __name__ == "__main__":
    import uvicorn

    if WEBHOOK_URL:
        async def webhook_mode():
            print("Initializing application for webhook...")
            await app.initialize()
            await app.start()
            print(f"Setting webhook to: {WEBHOOK_URL}")
            set_ok = await bot.set_webhook(url=WEBHOOK_URL)
            if set_ok:
                print("Webhook set successfully! Bot is LIVE 🔥")
            else:
                print("Failed to set webhook")
            asyncio.create_task(cleanup_task())
            uvicorn.run(api, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
        asyncio.run(webhook_mode())
    else:
        async def polling_mode():
            await app.initialize()
            await app.start()
            asyncio.create_task(cleanup_task())
            print("Bot running in polling mode (Termux)")
            await app.updater.start_polling(drop_pending_updates=True)
            await asyncio.Event().wait()
        asyncio.run(polling_mode())
