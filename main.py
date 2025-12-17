import asyncio
import os
from datetime import datetime, timedelta

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest

# Load .env
load_dotenv()

# Debug token load
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
print(f"Loaded bot token: {TOKEN[:10]}...{TOKEN[-10:] if TOKEN else 'MISSING'}")

if not TOKEN:
    print("FATAL: No bot token! Fix .env")
    exit(1)

# Config
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET", "").lower().strip()
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY", "").strip()
PREMIUM_CHANNEL_ID = int(os.getenv("PREMIUM_CHANNEL_ID", "0"))
PREMIUM_GROUP_ID = int(os.getenv("PREMIUM_GROUP_ID", "0"))

# Prices
MONTHLY_ETH = 0.0033
LIFETIME_ETH = 0.0167

# Custom request with HIGH timeouts for Termux/mobile networks
request = HTTPXRequest(
    connect_timeout=60.0,
    read_timeout=60.0,
    write_timeout=60.0,
    pool_timeout=60.0,
)

# Bot application with custom request
tg_app = Application.builder().token(TOKEN).request(request).build()
bot = tg_app.bot

# Storage
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
        print(f"Grant access error: {e}")

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
                print(f"Cleanup error: {e}")
            del subscriptions[uid]
        await asyncio.sleep(3600)

# Commands (same professional messages)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Welcome to ICE GODS ICE DEVILS Premium 🔥\n\n"
        "/plans - See plans\n/subscribe - Get wallet\n/status - Check access"
    )

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 PLANS 💎\n\n"
        f"📅 Monthly: {MONTHLY_ETH} ETH\n"
        f"👑 Lifetime: {LIFETIME_ETH} ETH+\n\n"
        "/subscribe to pay"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not PAYMENT_WALLET:
        await update.message.reply_text("Wallet error - contact admin")
        return
    await update.message.reply_text(
        f"💰 Send to:\n`{PAYMENT_WALLET}`\n\n"
        f"Monthly: {MONTHLY_ETH} ETH\n"
        f"Lifetime: {LIFETIME_ETH} ETH+\n\n"
        "/paid <tx_hash>",
        parse_mode=ParseMode.MARKDOWN
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid in subscriptions:
        exp = datetime.fromtimestamp(subscriptions[uid])
        if exp.year > 2050:
            await update.message.reply_text("👑 LIFETIME ACCESS 🔥")
        else:
            await update.message.reply_text(f"📅 Active until {exp.strftime('%Y-%m-%d')}")
    else:
        await update.message.reply_text("❌ No access - /plans")

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ /paid <tx_hash>")
        return
    tx = context.args[0].strip().lower()
    if payments.get(tx):
        await update.message.reply_text("✅ Already processed")
        return

    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={tx}&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=60) as resp:
            data = await resp.json()

    if not data.get("result"):
        await update.message.reply_text("❌ TX not found/pending")
        return

    tx_data = data["result"]
    to = tx_data.get("to", "").lower()
    value_eth = int(tx_data["value"], 16) / 10**18

    if to != PAYMENT_WALLET:
        await update.message.reply_text("❌ Wrong wallet")
        return

    uid = update.message.from_user.id
    await record_payment(tx, uid, value_eth)

    if value_eth >= LIFETIME_ETH:
        await activate(uid, lifetime=True)
        await update.message.reply_text("👑 LIFETIME ACCESS GRANTED! Welcome God 🔥")
    elif value_eth >= MONTHLY_ETH:
        await activate(uid, lifetime=False)
        await update.message.reply_text("📅 Monthly access granted! 🚀")
    else:
        await update.message.reply_text(f"❌ Need ≥ {MONTHLY_ETH} ETH")

# FastAPI for webhook
api = FastAPI()

@api.post("/webhook")
async def webhook(req: Request):
    json_data = await req.json()
    update = Update.de_json(json_data, bot)
    await tg_app.process_update(update)
    return {"ok": True}

@api.get("/health")
def health():
    return {"status": "ok"}

# Main
if __name__ == "__main__":
    import uvicorn

    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("plans", plans))
    tg_app.add_handler(CommandHandler("subscribe", subscribe))
    tg_app.add_handler(CommandHandler("status", status))
    tg_app.add_handler(CommandHandler("paid", paid))

    if WEBHOOK_URL:
        async def webhook_mode():
            await bot.set_webhook(WEBHOOK_URL)
            asyncio.create_task(cleanup_task())
            uvicorn.run(api, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
        asyncio.run(webhook_mode())
    else:
        async def polling_mode():
            await tg_app.initialize()
            await tg_app.start()
            asyncio.create_task(cleanup_task())
            print("🤖 BOT ONLINE - Polling (Termux mode)")
            print("🔥 ICE GODS ICE DEVILS Ready for payments 🔥")
            await tg_app.updater.start_polling(drop_pending_updates=True)
            await asyncio.Event().wait()

        asyncio.run(polling_mode())
