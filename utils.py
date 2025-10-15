# utils.py
import os, time, decimal
from decimal import Decimal
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def now_ts():
    return int(time.time())

def human_time(ts):
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")

def plan_to_seconds(plan):
    plan = plan.lower()
    if plan == "daily": return 24*3600
    if plan == "weekly": return 7*24*3600
    if plan == "monthly": return 30*24*3600
    if plan == "yearly": return 365*24*3600
    raise ValueError("unknown plan")
