# Telegram ETH Subscription Bot

A professional, production-ready Telegram subscription bot using **FastAPI** and **python-telegram-bot**.

---

## Features

- Webhook-only (Render-compatible, no polling)
- Single ETH wallet for all payments
- Manual subscription verification
- Subscription plans: Monthly / Lifetime
- SQLite database (no server)
- Health endpoint for monitoring

---

## Setup

1. **Copy `.env.example` to `.env`** and fill in your values:

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_ID=YOUR_TELEGRAM_ID_HERE
WEB
