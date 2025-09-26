import os
import asyncio
import logging
import time
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes

from subscriptions import PLANS
from database import (
    add_pending_payment_request,
    get_pending_payment_requests,
    mark_payment_processed,
    add_subscription,
    get_latest_subscription,
)
from payments import get_crypto_price, verify_eth_payment, verify_sol_payment
from handlers import make_plans_keyboard
from register_handlers import register_handlers
from manual_handlers import manual_safe_run

# Load env
BOT_TOKEN = os.environ.get("BOT_TOKEN")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SAFE_ETH_WALLET = os.environ.get("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.environ.get("SAFE_SOL_WALLET")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💎 Welcome! Use /plans to view subscription plans.")

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = make_plans_keyboard(PLANS)
    await update.message.reply_text("Choose a subscription plan:", reply_markup=reply_markup)

async def my_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = get_latest_subscription(user_id)
    if sub:
        expires = datetime.fromtimestamp(sub["expires_ts"])
        await update.message.reply_text(f"Your plan: {sub['plan']} — expires {expires}")
    else:
        await update.message.reply_text("You have no active subscription. Use /plans to subscribe.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data:
        return    if query.data.startswith("plan:"):
        plan_name = query.data.split(":", 1)[1]
        if plan_name not in PLANS:
            await query.message.reply_text("Invalid plan.")
            return

        usd_price = PLANS[plan_name]["price"]
        eth_price = get_crypto_price("ETH")
        sol_price = get_crypto_price("SOL")

        if eth_price is None or sol_price is None:
            await query.message.reply_text("Price service unavailable. Try again later.")
            return

        expected_eth = round(usd_price / eth_price, 6)
        expected_sol = round(usd_price / sol_price, 6)

        add_pending_payment_request(query.from_user.id, plan_name, "ETH", expected_eth)
        add_pending_payment_request(query.from_user.id, plan_name, "SOL", expected_sol)

        text = (
            f"Payment instructions for *{plan_name}*:\n\n"
            f"ETH: `{expected_eth}` to `{SAFE_ETH_WALLET}`\n\n"
            f"SOL: `{expected_sol}` to `{SAFE_SOL_WALLET}`\n\n"
            "After payment is broadcast, the bot will check and activate the subscription."
        )
        await query.message.reply_text(text, parse_mode="Markdown")

# --- Periodic Payment Check ---
async def check_payments_periodically(context: ContextTypes.DEFAULT_TYPE):
    pending = get_pending_payment_requests()
    for p in pending:
        tid = int(p["telegram_id"])
        plan = p["plan"]
        chain = p["chain"]
        expected = p["expected_amount"]
        is_paid = False
        tx_hash = None

        if chain == "ETH":
            is_paid = verify_eth_payment(expected)
        elif chain == "SOL":
            is_paid = verify_sol_payment(expected)

        if is_paid:
            mark_payment_processed(p["id"], tx_hash=tx_hash)
            plan_details = PLANS[plan]
            duration_days = plan_details["duration"]
            start_ts = int(time.time())
            expires_ts = start_ts + int(duration_days) * 86400 if duration_days else start_ts + 365*86400*100
            add_subscription(tid, plan, start_ts, expires_ts)
            try:
                await context.bot.send_message(chat_id=tid, text=f"✅ Payment received. Subscription activated: {plan}")
            except Exception:
                logger.exception("Failed sending confirmation message")

# --- Startup ---
async def on_startup(app):
    app.job_queue.run_repeating(lambda ctx: manual_safe_run(check_payments_periodically, ctx), interval=POLL_INTERVAL)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN missing in environment")
        return
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    register_handlers(app, start_command, plans_command, my_subscription_command, button_handler)
    app.post_init = on_startup
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
