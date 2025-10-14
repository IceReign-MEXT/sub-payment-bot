#!/bin/bash

# Activate virtualenv
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Load .env
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    exit 1
fi
echo ".env found and loaded."

# Start backend
echo "Starting backend..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 5

# Test backend
echo "Testing backend health endpoint..."
curl -s http://127.0.0.1:8000/api/health

# Start bot
echo "Starting Telegram bot..."
python3 deploy_bot.py &
BOT_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Bot PID: $BOT_PID"
echo "Press CTRL+C to stop both."
wait $BACKEND_PID $BOT_PID
