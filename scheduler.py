# scheduler.py
import os, asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from database import get_pending_payments, confirm_payment, upsert_user_subscribe, add_payment
from blockchain import sol_get_balance, eth_is_confirmed, eth_get_tx
from utils import now_ts, plan_to_seconds

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
SWEEP_INTERVAL = int(os.getenv("SWEEP_INTERVAL", "120"))

async def verify_payments_once():
    print("[scheduler] running verification sweep...")
    rows = get_pending_payments()
    for p in rows:
        chain = p["chain"].lower()
        addr = p["addr"]
        pid = p["id"]
        user_id = p["user_id"]
        amount = float(p["amount"])
        if chain == "sol":
            bal = await sol_get_balance(addr)
            if bal and bal >= amount:
                # confirm
                confirm_payment(pid, tx_hash=None)
                start = now_ts()
                end = start + plan_to_seconds("monthly")  # default: set plan later
                upsert_user_subscribe(user_id, None, "monthly", start, end)
                print(f"[scheduler] SOL payment confirmed for {user_id}")
        elif chain == "eth":
            # this is an example: in production you'd detect the tx hash first
            # here we try to find a tx by scanning mempool or via third-party
            # assume `p.tx_hash` present else skip
            if p.get("tx_hash"):
                if eth_is_confirmed(p["tx_hash"], required=int(os.getenv("ETH_CONFIRMATIONS", "3"))):
                    confirm_payment(pid, tx_hash=p["tx_hash"])
                    start = now_ts()
                    end = start + plan_to_seconds("monthly")
                    upsert_user_subscribe(user_id, None, "monthly", start, end)
                    print(f"[scheduler] ETH payment confirmed for {user_id}")

async def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(verify_payments_once()), "interval", seconds=SWEEP_INTERVAL)
    scheduler.start()
    print("[scheduler] started")
