#!/bin/bash
set -e

echo "Starting Python bot..."
python bot.py &

echo "Starting run_bot.sh..."
bash run_bot.sh &

# Wait for both to finish (keeps container alive)
wait