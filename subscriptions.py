# Subscription plans with price (USD) and duration (days)
PLANS = {
    "Daily": {"price": 5, "duration": 1},
    "Weekly": {"price": 20, "duration": 7},
    "Monthly": {"price": 50, "duration": 30},
    "Yearly": {"price": 500, "duration": 365},
    "Lifetime": {"price": 1000, "duration": None}, # Use None for lifetime, handled in duration calculation
}

# You can add more subscription-related logic here if needed
# For example, checking if a user has an active subscription etc.

