#!/usr/bin/env python3
# test_connections.py - Simple checks for Telegram bot token, ETH and SOL RPCs

import os, sys, json, asyncio
import requests

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_RPC = os.getenv("ETH_RPC_URL") or os.getenv("INFURA_API")
SOL_RPC = os.getenv("SOLANA_RPC_URL")

def check_telegram():
    if not BOT_TOKEN:
        return False, "BOT_TOKEN not set"
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
        if r.status_code == 200:
            j = r.json()
            if j.get("ok"):
                return True, f"Telegram OK - @{j['result'].get('username')}"
        return False, f"Telegram returned status {r.status_code}"
    except Exception as e:
        return False, f"Telegram exception: {e}"

def check_eth():
    if not ETH_RPC:
        return False, "ETH_RPC_URL not set"
    try:
        payload = {"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}
        r = requests.post(ETH_RPC, json=payload, timeout=10)
        if r.status_code == 200:
            return True, f"ETH RPC OK (response sample: {r.text[:120]})"
        return False, f"ETH RPC status {r.status_code}"
    except Exception as e:
        return False, f"ETH RPC exception: {e}"

def check_solana():
    if not SOL_RPC:
        return False, "SOLANA_RPC_URL not set"
    try:
        payload = {"jsonrpc":"2.0","id":1,"method":"getHealth","params":[]}
        r = requests.post(SOL_RPC, json=payload, timeout=10)
        if r.status_code == 200:
            return True, f"SOL RPC OK (response sample: {r.text[:120]})"
        # fallback to getVersion
        payload2 = {"jsonrpc":"2.0","id":1,"method":"getVersion","params":[]}
        r2 = requests.post(SOL_RPC, json=payload2, timeout=10)
        if r2.status_code == 200:
            return True, f"SOL RPC version OK (sample: {r2.text[:120]})"
        return False, f"SOL RPC status {r.status_code}"
    except Exception as e:
        return False, f"SOL RPC exception: {e}"

if __name__ == "__main__":
    print("=== Running quick connectivity checks ===")
    tg_ok, tg_msg = check_telegram()
    print("Telegram:", tg_ok, "-", tg_msg)
    eth_ok, eth_msg = check_eth()
    print("Ethereum RPC:", eth_ok, "-", eth_msg)
    sol_ok, sol_msg = check_solana()
    print("Solana RPC:", sol_ok, "-", sol_msg)
    # quick exit code behavior
    if tg_ok and eth_ok and sol_ok:
        sys.exit(0)
    sys.exit(1)
