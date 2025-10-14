#!/usr/bin/env python3
"""
Audit & Deploy-check for sub-payment-bot repository.
"""

import os, re, json, sys, subprocess, traceback
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

ROOT = Path('.').resolve()
REPORT_MD = ROOT / "audit_report.md"
REPORT_JSON = ROOT / "audit_report.json"

# ---------- Config ----------
REQUIRED_ENV_KEYS = [
    "BOT_TOKEN",
    "ADMIN_ID",
    "SAFE_SOL_WALLET",
    "SAFE_ETH_WALLET",
    "SOLANA_RPC_URL",
    "INFURA_KEY",
    "DATABASE_URL",
    "MODE"
]

WALLET_REGEX = {
    "ETH": re.compile(r"^0x[a-fA-F0-9]{40}$"),
    "SOL": re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")  # rough
}

PYTHON_FILES = list(ROOT.glob("*.py"))
DEPLOY_FILES = ["Procfile", "render_deploy_auto.py", "render_auto_restart.py"]

# ---------- Helpers ----------
def read_env_file(p=".env"):
    path = Path(p)
    res = {"ok": False, "path": str(path), "lines": [], "vars": {}, "errors": []}
    if not path.exists():
        res["errors"].append("No .env file found")
        return res

    raw = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    res["lines"] = raw

    for i, ln in enumerate(raw, start=1):
        ln_stripped = ln.strip()
        if not ln_stripped or ln_stripped.startswith("#"):
            continue
        if ln_stripped.startswith(("<<<<<<<", "=======", ">>>>>>>")):
            res["errors"].append(f"Conflict marker on line {i}")
            continue
        if "=" not in ln_stripped:
            res["errors"].append(f"Malformed line {i}: {ln}")
            continue

        key, val = ln_stripped.split("=", 1)
        key = key.strip()
        val = val.strip()

        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
            res["errors"].append(f"Value for {key} had quotes removed")

        if "#" in val:
            val = val.split("#", 1)[0].strip()
            res["errors"].append(f"Inline comment removed from value for {key}")

        res["vars"][key] = val

    res["ok"] = True if res["vars"] else False
    return res


def try_imports(pkgs):
    result = {}
    for pkg in pkgs:
        try:
            __import__(pkg)
            result[pkg] = {"installed": True}
        except Exception as e:
            result[pkg] = {"installed": False, "error": str(e)}
    return result


def test_rpc(url, timeout=6):
    if not requests:
        return {"ok": False, "reason": "requests not installed locally"}
    try:
        r = requests.get(url, timeout=timeout)
        return {"ok": True, "status_code": r.status_code, "text_snippet": r.text[:100]}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def validate_telegram_token(token):
    if not token:
        return {"ok": False, "reason": "no token provided"}
    if not requests:
        return {"ok": False, "reason": "requests not installed"}

    token = token.strip()
    m = re.match(r"^\d{6,}:[A-Za-z0-9_\-]{10,}$", token)
    if not m:
        return {"ok": False, "reason": "token format looks invalid"}
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=6)
        j = r.json()
        return {"ok": j.get("ok", False), "status_code": r.status_code, "response": j}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def detect_polling_vs_webhook(files):
    summary = {"uses_polling": [], "uses_web_framework": [], "notes": []}
    for f in files:
        txt = Path(f).read_text(errors="ignore")
        if "run_polling" in txt or ".run_polling" in txt:
            summary["uses_polling"].append(f)
        if any(x in txt for x in ["FastAPI", "Flask", "uvicorn", "gunicorn", "app.post", "app.get", "webhook"]):
            summary["uses_web_framework"].append(f)
    return summary


if __name__ == "__main__":
    print("✅ audit_and_deploy_check.py syntax OK — ready to run.")
