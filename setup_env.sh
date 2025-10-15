#!/usr/bin/env bash
# setup_env.sh
# Termux-friendly environment setup and pinned installs to avoid Rust builds.

set -euo pipefail
echo "==> Running setup_env.sh - pinned installs for Termux"

# 1) Ensure python3 & venv are available
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python in Termux and retry."
  exit 1
fi

# 2) Create venv if not exists
if [ ! -d "venv" ]; then
  echo "==> Creating venv..."
  python3 -m venv venv
fi

# 3) Activate venv
echo "==> Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

# 4) Upgrade pip / wheel / setuptools to latest stable
echo "==> Upgrading pip, wheel, setuptools..."
pip install --upgrade pip setuptools wheel

# 5) Install pinned packages that avoid Rust builds
# pinned versions chosen to avoid pydantic-core (Rust) compilation
echo "==> Installing pinned packages..."
pip install "pydantic==1.10.13" \
            "web3==6.5.0" \
            "python-telegram-bot==20.6" \
            "python-dotenv==1.0.1" \
            "aiohttp==3.9.1" \
            "requests==2.31.0" \
            "psycopg2-binary==2.9.9" \
            "aiosqlite==0.19.0" \
            "solana==0.30.2" || {
  echo "ERROR: pip install failed. See errors above."
  echo "Try running: pip install pydantic==1.10.13 web3==6.5.0"
  exit 2
}

# 6) Extra: ensure common development helpers installed
pip install --upgrade virtualenv

echo "==> All packages installed into venv successfully."
echo "==> To activate: source venv/bin/activate"
echo "==> Run 'bash test_connections.sh' next to verify connectivity."
