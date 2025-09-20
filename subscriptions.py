from telegram import Update
from telegram.ext import ContextTypes

# Subscription plans
PLANS = {
    "Daily": {"price": 7, "duration": 1},       # 1 day
    "Weekly": {"price": 15, "duration": 7},     # 7 days
    "Monthly": {"price": 100, "duration": 30},  # 30 days
    "Yearly": {"price": 1200, "duration": 365}, # 365 days
    "Lifetime": {"price": 1600, "duration": None}  # No expiry
}

# Handle subscription request
async def handle_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str):
    user = update.callback_query.from_user
    details = PLANS.get(plan)

    if not details:
        await update.callback_query.message.reply_text("❌ Invalid plan selected.")
        return

    # For now just show price (payment logic comes later)
    price = details["price"]
    duration = "Lifetime" if details["duration"] is None else f"{details['duration']} days"

    await update.callback_query.message.reply_text(
        f"📌 You selected *{plan} Plan*.\n\n"
        f"💵 Price: ${price}\n"
        f"⏳ Duration: {duration}\n\n"
        f"✅ Payment instructions will follow soon...",
        parse_mode="Markdown"
    )

    # Log to console
    print(f"User @{user.username} ({user.id}) selected {plan} plan.")
