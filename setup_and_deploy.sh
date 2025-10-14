#!/bin/bash
# ===========================
# IceGODS Sub-Payment-Bot Full Setup & Deploy
# ===========================

# 1️⃣ Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment not found, creating..."
    python3 -m venv venv
    source venv/bin/activate
fi

# 2️⃣ Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# 3️⃣ Install dependencies (compatible versions)
echo "Installing required packages..."
python -m pip install requests
python -m pip install python-telegram-bot==20.7
python -m pip install solana==0.27.0 httpx==0.23.3
python -m pip install aiogram fastapi uvicorn pydantic pydantic-core asyncpg SQLAlchemy

# 4️⃣ Export environment variables
echo "Exporting environment variables..."
export BOT_TOKEN="8018403994:AAGjxumideAy9XhFIFuXiYHTerUgsIPjieg"
export ADMIN_ID="6453658778"
export SAFE_SOL_WALLET="HxmywH2gW9ezQ2nBXwurpaWsZS6YvdmLF23R9WgMAM7p"
export SAFE_ETH_WALLET="0x5B0703825e5299b52b0d00193Ac22E20795defBa"
export DATABASE_URL="postgresql://user:password@localhost:5432/subpaymentdb"
export RENDER_API_KEY="rnd_Ua5ub86vlyCyof5gPSNRRsZBaJwc"
export RENDER_SERVICE_ID="tea-d3lfuaemcj7s739td7hg"

# 5️⃣ Verify Render service exists
echo "Checking Render service..."
curl -H "Authorization: Bearer $RENDER_API_KEY" https://api.render.com/v1/services | jq .

# 6️⃣ Push to GitHub
echo "Adding, committing, and pushing changes..."
git add .
git commit -m "Full environment & dependency fix"
git pull origin main
git push origin main

# 7️⃣ Trigger redeploy on Render
echo "Triggering Render redeploy..."
curl -X POST \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"clearCache": true}' \
  "https://api.render.com/v1/services/$RENDER_SERVICE_ID/deploys"

echo "✅ Setup & deploy script finished!"
