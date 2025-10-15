#!/usr/bin/env python3
"""
master_integrity.py
Master integrity & monitoring guardian for ICEGODSDEVILGODS Sub-Payment Bot.

Features:
 - Validates environment and required Python modules
 - Attempts safe fixes (pip install missing packages)
 - Tests Telegram bot connectivity and notifies ADMIN_ID
 - Tests Ethereum + Solana connectivity
 - Monitors receiving wallets for incoming payments (notifies admin)
 - Monitors SAFE wallets for balance drops (alerts)
 - Can run once (--once) or run continuously (--loop --interval N)
 - DOES NOT move funds or perform trades — notifications only.
"""

import os
import sys
import time
import json
import argparse
import asyncio
import subprocess
import logging
from typing import List, Dict, Optional

# Basic libs that should exist
import requests

# Try optional imports; install if missing
OPTIONAL_PACKAGES = [
    ("web3", "web3"),
    ("aiohttp", "aiohttp"),
    ("aiosqlite", "aiosqlite"),
    ("asyncpg", "asyncpg"),
    ("python_dotenv", "python-dotenv"),  # install name
]

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("master_integrity")

# ---------- Utility functions ----------
def pip_install(pkg_name: str):
    """Attempt pip install into current Python env."""
    log.info(f"Attempting to pip install: {pkg_name}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
        log.info(f"Installed: {pkg_name}")
        return True
    except Exception as e:
        log.error(f"Failed to install {pkg_name}: {e}")
        return False

def ensure_imports():
    """Try importing optional packages, install them when missing."""
    missing = []
    try:
        import web3  # type: ignore
    except Exception:
        missing.append("web3==6.5.0")
    try:
        import aiohttp  # type: ignore
    except Exception:
        missing.append("aiohttp")
    try:
        import aiosqlite  # type: ignore
    except Exception:
        missing.append("aiosqlite")
    try:
        import asyncpg  # type: ignore
    except Exception:
        # asyncpg optional: only needed if using Postgres
        missing.append("asyncpg")
    try:
        import dotenv  # type: ignore
    except Exception:
        missing.append("python-dotenv")
    if missing:
        log.warning("Missing python packages: %s", missing)
        for pkg in missing:
            pip_install(pkg)

# ---------- Load env safely ----------
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
if ADMIN_ID is not None:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except Exception:
        log.warning("ADMIN_ID not integer; leaving as string.")

# RPC & wallets
ETH_RPC_URL = os.getenv("ETH_RPC_URL") or os.getenv("INFURA_API")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
RECEIVING_ETH = os.getenv("RECEIVING_ETH") or os.getenv("ETH_WALLET")
RECEIVING_SOL = os.getenv("RECEIVING_SOL") or os.getenv("SOL_WALLET")
SAFE_ETH_WALLET = os.getenv("SAFE_ETH_WALLET")
SAFE_SOL_WALLET = os.getenv("SAFE_SOL_WALLET")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")  # optional (for TX listing)
DATABASE_URL = os.getenv("DATABASE_URL")

MODE = os.getenv("MODE", "testing")

# Notifications helper (Telegram sendMessage)
def telegram_notify(text: str):
    """Send a message to ADMIN_ID via Bot API (simple, no extra deps)."""
    if not BOT_TOKEN or not ADMIN_ID:
        log.warning("BOT_TOKEN or ADMIN_ID missing; cannot notify.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_ID, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            log.info("Notified admin via Telegram")
            return True
        else:
            log.error("Telegram notify failed: %s %s", r.status_code, r.text)
            return False
    except Exception as e:
        log.exception("Telegram notify exception: %s", e)
        return False

# ---------- Service tests ----------
def check_telegram():
    """Check Bot token validity using getMe."""
    if not BOT_TOKEN:
        return False, "BOT_TOKEN missing"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            j = r.json()
            if j.get("ok"):
                bot_user = j.get("result", {}).get("username")
                return True, f"Telegram OK (bot @{bot_user})"
        return False, f"Telegram check failed: {r.status_code} {r.text}"
    except Exception as e:
        return False, f"Telegram exception: {e}"

def check_eth_connection():
    """Check Ethereum provider via web3."""
    try:
        from web3 import Web3  # type: ignore
    except Exception as e:
        return False, f"web3 import error: {e}"
    if not ETH_RPC_URL:
        return False, "ETH_RPC_URL not set"
    try:
        w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL, request_kwargs={"timeout": 10}))
        if w3.is_connected():
            chain = w3.eth.chain_id
            return True, f"Web3 connected (chain_id={chain})"
        return False, "Web3 not connected"
    except Exception as e:
        return False, f"Web3 exception: {e}"

async def check_solana_rpc():
    """Ping Solana getVersion or getHealth to verify RPC responsiveness."""
    import aiohttp  # type: ignore
    if not SOLANA_RPC_URL:
        return False, "SOLANA_RPC_URL not set"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SOLANA_RPC_URL, json={"jsonrpc":"2.0","id":1,"method":"getHealth"}) as resp:
                j = await resp.json()
                # Some endpoints do not support getHealth; fallback to getVersion
                if resp.status == 200:
                    return True, f"Solana RPC OK"
            # fallback
            async with aiohttp.ClientSession() as session:
                async with session.post(SOLANA_RPC_URL, json={"jsonrpc":"2.0","id":1,"method":"getVersion"}) as resp:
                    if resp.status == 200:
                        return True, "Solana RPC version OK"
    except Exception as e:
        return False, f"Solana RPC exception: {e}"
    return False, "Unknown Solana RPC error"

def check_database():
    """Attempt a lightweight connectivity check for DATABASE_URL if using asyncpg, else skip."""
    try:
        import asyncpg  # type: ignore
    except Exception:
        return False, "asyncpg not installed"
    if not DATABASE_URL:
        return False, "DATABASE_URL not set"
    # Basic try/catch to attempt a connection (sync call using asyncio)
    async def _check():
        try:
            conn = await asyncpg.connect(DATABASE_URL, timeout=5)
            await conn.close()
            return True, "Database connected"
        except Exception as e:
            return False, f"Database exception: {e}"
    try:
        ok, msg = asyncio.run(_check())
        return ok, msg
    except Exception as e:
        return False, f"Database check exception: {e}"

# ---------- Blockchain watchers (simple) ----------
def fetch_eth_txs_from_etherscan(address: str, api_key: Optional[str]):
    """Fetch recent normal transactions for an address using Etherscan API (fallback)."""
    if not api_key:
        return []
    try:
        url = (
            "https://api.etherscan.io/api"
            f"?module=account&action=txlist&address={address}"
            "&startblock=0&endblock=99999999&sort=desc"
            f"&apikey={api_key}"
        )
        r = requests.get(url, timeout=20)
        j = r.json()
        if j.get("status") == "1":
            return j.get("result", [])
        return []
    except Exception as e:
        log.exception("Etherscan fetch error: %s", e)
        return []

async def get_solana_signatures(address: str, limit: int = 10):
    import aiohttp  # type: ignore
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SOLANA_RPC_URL, json={"jsonrpc":"2.0","id":1,"method":"getSignaturesForAddress","params":[address, {"limit": limit}]}) as resp:
                j = await resp.json()
                return j.get("result", [])
    except Exception as e:
        log.exception("Solana signatures error: %s", e)
        return []

# Monitoring state (in-memory)
STATE = {
    "seen_eth_txs": set(),
    "seen_sol_sigs": set(),
    "last_safe_eth_balance": None,
    "last_safe_sol_balance": None,
}

def eth_balance_alert_threshold_change(prev: float, curr: float, threshold_pct: float = 0.1) -> bool:
    """Alert if balance dropped by more than threshold_pct (10% default)."""
    if prev is None:
        return False
    try:
        if prev <= 0:
            return False
        drop = (prev - curr) / prev
        return drop >= threshold_pct
    except Exception:
        return False

def sol_balance_alert_threshold_change(prev: float, curr: float, threshold_pct: float = 0.1) -> bool:
    return eth_balance_alert_threshold_change(prev, curr, threshold_pct)

# ---------- Watcher implementations ----------
def check_eth_incoming_and_safe(wallet_receiving: str, safe_wallet: Optional[str]):
    """Check incoming txs to receiving address via Etherscan (if key provided) or check recent txs with web3."""
    try:
        from web3 import Web3  # type: ignore
    except Exception:
        log.debug("web3 not present for eth checking")
        return []
    results = []
    # Prefer Etherscan if API key available
    if ETHERSCAN_API_KEY:
        txs = fetch_eth_txs_from_etherscan(wallet_receiving, ETHERSCAN_API_KEY)
        for tx in txs[:10]:
            txhash = tx.get("hash")
            if not txhash or txhash in STATE["seen_eth_txs"]:
                continue
            STATE["seen_eth_txs"].add(txhash)
            from_addr = tx.get("from")
            value = int(tx.get("value", "0"))
            eth_value = value / 1e18
            results.append(("incoming", txhash, from_addr, eth_value))
    else:
        # Fallback: use web3 to get latest block txs (expensive) — skip for now
        log.debug("No etherscan key; skipping detailed tx scan")
    # Safe wallet balance check
    if safe_wallet:
        try:
            w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
            bal = w3.eth.get_balance(Web3.to_checksum_address(safe_wallet)) / 1e18
            prev = STATE.get("last_safe_eth_balance")
            STATE["last_safe_eth_balance"] = bal
            if eth_balance_alert_threshold_change(prev, bal, threshold_pct=0.1):
                results.append(("safe_drop", safe_wallet, prev, bal))
        except Exception as e:
            log.exception("Error checking safe eth balance: %s", e)
    return results

async def check_solana_incoming_and_safe(wallet_receiving: str, safe_wallet: Optional[str]):
    out = []
    try:
        sigs = await get_solana_signatures(wallet_receiving, limit=5)
        for s in sigs:
            sig = s.get("signature")
            if not sig or sig in STATE["seen_sol_sigs"]:
                continue
            STATE["seen_sol_sigs"].add(sig)
            out.append(("sig", sig))
    except Exception:
        log.exception("Solana incoming check failed")
    # safe wallet balance check
    try:
        bal = None
        if safe_wallet:
            async with __import__('aiohttp').ClientSession() as session:  # type: ignore
                async with session.post(SOLANA_RPC_URL, json={"jsonrpc":"2.0","id":1,"method":"getBalance","params":[safe_wallet]}) as resp:
                    j = await resp.json()
                    bal = j.get("result", {}).get("value", 0) / 1e9
            prev = STATE.get("last_safe_sol_balance")
            STATE["last_safe_sol_balance"] = bal
            if sol_balance_alert_threshold_change(prev, bal, threshold_pct=0.1):
                out.append(("safe_drop_sol", safe_wallet, prev, bal))
    except Exception:
        log.exception("Solana safe balance check error")
    return out

# ---------- High-level orchestrator ----------
async def run_checks_and_repairs_once():
    """Run all checks once, attempt safe repairs, and notify admin of results."""
    log.info("Running master integrity checks (one-shot).")
    ensure_imports()

    # 1) Telegram
    ok, msg = check_telegram()
    log.info("Telegram: %s - %s", ok, msg)
    if not ok:
        telegram_notify(f"⚠️ Telegram check failed: {msg}")
        # No safe repair for bot token; admin must fix.

    # 2) Web3 / Ethereum
    ok_eth, msg_eth = check_eth_connection()
    log.info("Ethereum: %s - %s", ok_eth, msg_eth)
    if not ok_eth:
        telegram_notify(f"⚠️ Ethereum RPC problem: {msg_eth}")

    # 3) Solana RPC
    ok_sol, msg_sol = await check_solana_rpc()
    log.info("Solana: %s - %s", ok_sol, msg_sol)
    if not ok_sol:
        telegram_notify(f"⚠️ Solana RPC problem: {msg_sol}")

    # 4) Database
    ok_db, msg_db = check_database()
    log.info("Database: %s - %s", ok_db, msg_db)
    if not ok_db:
        telegram_notify(f"⚠️ Database problem: {msg_db}")

    # 5) Blockchain watchers (non-blocking)
    try:
        eth_events = check_eth_incoming_and_safe(RECEIVING_ETH, SAFE_ETH_WALLET)
        for ev in eth_events:
            if ev[0] == "incoming":
                txhash, sender, amount = ev[1], ev[2], ev[3]
                text = f"✅ ETH Payment detected\nFrom: {sender}\nAmount: {amount:.6f} ETH\nTX: https://etherscan.io/tx/{txhash}"
                telegram_notify(text)
            elif ev[0] == "safe_drop":
                _, wallet, prev, bal = ev
                telegram_notify(f"⚠️ SAFE ETH balance drop detected for {wallet}\nPrev: {prev}\nNow: {bal}")
    except Exception:
        log.exception("Error processing ETH events")

    try:
        sol_events = await check_solana_incoming_and_safe(RECEIVING_SOL, SAFE_SOL_WALLET)
        for ev in sol_events:
            if ev[0] == "sig":
                sig = ev[1]
                telegram_notify(f"✅ SOL Activity detected on {RECEIVING_SOL}\nSignature: {sig}\nTX: https://explorer.solana.com/tx/{sig}")
            elif ev[0] == "safe_drop_sol":
                _, wallet, prev, bal = ev
                telegram_notify(f"⚠️ SAFE SOL balance drop detected for {wallet}\nPrev: {prev}\nNow: {bal}")
    except Exception:
        log.exception("Error processing SOL events")

    log.info("One-shot checks finished.")
    telegram_notify("✅ Master integrity checks completed.")

async def guardian_loop(interval: int = 60):
    log.info("Starting guardian loop with interval %s seconds", interval)
    ensure_imports()
    # initial check
    await run_checks_and_repairs_once()
    while True:
        try:
            await asyncio.sleep(interval)
            await run_checks_and_repairs_once()
        except Exception as e:
            log.exception("Guardian loop error: %s", e)
            telegram_notify(f"🔴 Guardian error: {e}")

# ---------- CLI ----------
def parse_args():
    parser = argparse.ArgumentParser(description="Master Integrity Guardian")
    parser.add_argument("--once", action="store_true", help="Run checks once and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuous guardian loop")
    parser.add_argument("--interval", type=int, default=60, help="Loop interval seconds")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.once:
        asyncio.run(run_checks_and_repairs_once())
    elif args.loop:
        asyncio.run(guardian_loop(interval=args.interval))
    else:
        # default: run once then exit
        asyncio.run(run_checks_and_repairs_once())

if __name__ == "__main__":
    main()
