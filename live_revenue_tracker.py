import time
from datetime import datetime
import os
from telegram import Bot
from database import get_pending_payment_requests, mark_payment_processed
from subscriptions import PLANS, add_subscription
from payments import verify_eth_payment, verify_sol_payment

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

CHECK_INTERVAL = 60  # seconds

def track_payments():
    while True:
        pending = get_pending_payment_requests()
        for p in pending:
            user_id = int(p["telegram_id"])
            plan = p["plan"]
            chain = p["chain"]
            expected = p["expected_amount"]
            is_paid = False

            if chain == "ETH":
                is_paid = verify_eth_payment(expected)
            elif chain == "SOL":
                is_paid = verify_sol_payment(expected)

            if is_paid:
                mark_payment_processed(p["id"])
                plan_details = PLANS[plan]
                duration_days = plan_details["duration"]
                start_ts = int(time.time())
                expires_ts = start_ts + duration_days*86400 if duration_days else start_ts + 365*86400*100
                add_subscription(user_id, plan, start_ts, expires_ts)
                try:
                    bot.send_message(
                        chat_id=user_id,
                        text=f"✅ Payment confirmed for plan *{plan}*. Your subscription is active!",
                        parse_mode="Markdown"
                    )
                    print(f"[{datetime.now()}] Payment confirmed: User {user_id} - {plan}")
                except Exception as e:
                    print(f"[{datetime.now()}] Failed to notify user {user_id}: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    track_payments()
