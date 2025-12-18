import os
from fastapi import FastAPI, Request, Header, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

app = FastAPI()

tg_app = Application.builder().token(BOT_TOKEN).build()


# ──────────────────────────────
# Telegram commands
# ──────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot is live.\n\nPayment system initializing."
    )


tg_app.add_handler(CommandHandler("start", start))


# ──────────────────────────────
# Health check
# ──────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}


# ──────────────────────────────
# Telegram webhook
# ──────────────────────────────
@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    if WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret")

    payload = await request.json()
    update = Update.de_json(payload, tg_app.bot)
    await tg_app.process_update(update)
<<<<<<< HEAD
    return {"ok": True}
=======
    return {"ok": True}
>>>>>>> db1984f (Clean FastAPI Telegram webhook bot (stable))
