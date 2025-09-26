from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import add_pending_payment_request, get_latest_subscription

def make_plans_keyboard(plans):
    keyboard = []
    for name, details in plans.items():
        keyboard.append([InlineKeyboardButton(f"{name} — ${details['price']}", callback_data=f"plan:{name}")])
    return InlineKeyboardMarkup(keyboard)
