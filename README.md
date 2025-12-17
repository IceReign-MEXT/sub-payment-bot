# Telegram ETH Subscription Bot

A professional Telegram bot for managing paid subscriptions to private channels/groups using Ethereum (ETH) mainnet payments.

## Features
- Users view plans and subscribe
- Pay with real ETH to a specified wallet
- Manual transaction hash submission for verification via Etherscan
- Automatic access grant (invite to channel/group)
- Subscription status check
- Auto-cleanup for expired subscriptions
- Supports monthly and lifetime plans
- Deployable on Render, Railway, or locally (Termux/VPS)

## Setup
1. Create a bot via @BotFather and get TOKEN
2. Copy `.env.example` to `.env` and fill values
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python main.py` (polling) or deploy with webhook

## Environment Variables
- TELEGRAM_BOT_TOKEN: Your bot token
- ADMIN_ID: Your Telegram user ID
- PAYMENT_WALLET: ETH address to receive payments (lowercase)
- ETHERSCAN_KEY: Free API key from etherscan.io
- PREMIUM_CHANNEL_ID / PREMIUM_GROUP_ID: -100... IDs (bot must be admin with invite rights)
- WEBHOOK_URL: For production hosting (e.g., Render URL + /webhook)

## Deployment
- Free on Render.com (web service + Procfile)
- Or run locally with polling

**Warning**: Uses real mainnet ETH. Test carefully.

Made for reliable monetization of premium Telegram content.
