from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from subscriptions import PLANS, handle_subscription
from payments import generate_payment_address, check_payment
from database import add_subscription, check_subscription

# Show subscription plans
async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"Daily - ${PLANS['Daily']['price']}", callback_data="plan:Daily")],
        [InlineKeyboardButton(f"Weekly - ${PLANS['Weekly']['price']}", callback_data="plan:Weekly")],
        [InlineKeyboardButton(f"Monthly - ${PLANS['Monthly']['price']}", callback_data="plan:Monthly")],
        [InlineKeyboardButton(f"Yearly - ${PLANS['Yearly']['price']}", callback_data="plan:Yearly")],
        [InlineKeyboardButton(f"Lifetime - ${PLANS['Lifetime']['price']}", callback_data="plan:Lifetime")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("💎 *Choose a subscription plan:*", 
                                    reply_markup=reply_markup, parse_mode="Markdown")

# Handle button click
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("plan:"):
        plan = query.data.split(":")[1]
        await handle_subscription(update, context, plan)

        # Create unique wallet address for user
        address = generate_payment_address(query.from_user.id)
        await query.message.reply_text(
            f"💰 Please send *${PLANS[plan]['price']} USDT/ETH* to this address:\n\n"
            f"`{address}`\n\n"
            f"After sending, click /verify to activate.",
            parse_mode="Markdown"
        )

        # Save selected plan temporarily
        context.user_data["selected_plan"] = plan

# Verify payment
async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    plan = context.user_data.get("selected_plan")

    if not plan:
        await update.message.reply_text("⚠️ You have not selected a plan yet. Use /plans first.")
        return

    amount = PLANS[plan]["price"]
    paid = check_payment(user.id, amount)

    if paid:
        days = PLANS[plan]["duration"] or 9999  # Lifetime = big number
        add_subscription(user.id, user.username or "unknown", plan, days)

        await update.message.reply_text(
            f"✅ Payment confirmed!\n"
            f"🎉 You now have *{plan}* access."
        )
    else:
        await update.message.reply_text("❌ Payment not detected yet. Please try again later.")
