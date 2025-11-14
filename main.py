import os, asyncio, threading, re
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

if os.name != 'nt':
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

load_dotenv()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

PLANS = {"premium": {"name": "👑 Pro Access", "price": "0.1 ETH / month", "wallet": os.getenv("ETH_WALLET")}}

def validate_wallet(text):
    if re.match(r'^0x[a-fA-F0-9]{40}$', text): return "Ethereum"
    elif re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', text): return "Solana"
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👑 Welcome to *Pro Access*. Use /buy to subscribe."
    await update.message.reply_text(text, parse_mode="Markdown")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan = PLANS['premium']
    text = (f"Cost: {plan['price']}\nWallet: `{plan['wallet']}`\n\n"
            "After payment, paste your wallet address to verify.")
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text.strip()
    w_type = validate_wallet(wallet)
    user = update.effective_user.username or update.effective_user.first_name

    if w_type:
        await update.message.reply_text(f"✅ Wallet `{wallet}` linked. Waiting for payment...", parse_mode="Markdown")
        admin_msg = f"🚨 NEW WALLET: @{user}. Type: {w_type}. Wallet: `{wallet}`"
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Invalid address. Check and try again.")

# --- FASTAPI WEBHOOK SETUP ---
application = Application.builder().token(os.getenv("BOT_TOKEN")).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("buy", buy))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
app = FastAPI()

@app.post(f"/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"ok": True}

@app.get("/")
async def root(): return {"message": "Pro Payment Bot is LIVE."}

@app.on_event("startup")
async def startup_event():
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url: await application.bot.set_webhook(url=f"{webhook_url}/webhook")
    asyncio.create_task(application.run_polling()) # Process updates from queue
