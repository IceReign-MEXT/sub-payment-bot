import time
from datetime import datetime, timedelta
from database import get_pending_payment_requests, get_latest_subscription

# Pricing tiers in USD
PRICING = {
    "Starter": 5,
    "Intermediate": 15,
    "Premium": 50
}

def calculate_revenue():
    now = int(time.time())
    one_week_ago = now - 7*24*60*60
    one_month_ago = now - 30*24*60*60

    weekly_revenue = 0
    monthly_revenue = 0

    subscriptions = get_latest_subscription_all_users()  # create this DB helper if needed

    for sub in subscriptions:
        plan_name = sub["plan"]
        start_ts = sub["start_ts"]

        usd_price = PRICING.get(plan_name, 0)

        if start_ts >= one_week_ago:
            weekly_revenue += usd_price
        if start_ts >= one_month_ago:
            monthly_revenue += usd_price

    print(f"💰 Estimated revenue:")
    print(f"Weekly: ${weekly_revenue}")
    print(f"Monthly: ${monthly_revenue}")

if __name__ == "__main__":
    calculate_revenue()
