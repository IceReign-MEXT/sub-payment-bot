import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, DateTime, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from web3 import Web3
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
from bitcoinrpc.authproxy import AuthServiceProxy

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

ETH_WALLET = os.getenv("ETH_WALLET")
SOL_WALLET = os.getenv("SOL_WALLET")
BTC_WALLET = os.getenv("BTC_WALLET")

ETH_RPC_URL = os.getenv("ETH_RPC_URL")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")

DATABASE_URL = os.getenv("DATABASE_URL")
MODE = os.getenv("MODE", "production")

# -------------------------------
# Database setup
# -------------------------------
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, nullable=False)
    plan = Column(String, nullable=False)
    expires = Column(DateTime, nullable=False)
    wallet = Column(String, nullable=True)
    tx_hash = Column(String, nullable=True)
    currency = Column(String, nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# -------------------------------
# Subscription plans
# -------------------------------
PLANS = {
    "basic": {"name": "💎 Basic", "price": 10},      # USD
    "premium": {"name": "🔥 Premium", "price": 25},
    "ultimate": {"name": "👑 Ultimate", "price": 50},
}

# -------------------------------
# Telegram Handlers
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Welcome, *{user.first_name or 'User'}!* \n\n"
        "Welcome to *Ice Premium Subscriptions* ❄️\n\n"
        "🔥 Features:\n"
        "— Secure crypto payments\n"
        "— Multi-chain support: ETH, SOL, BTC\n"
        "— Auto-renewal options\n\n"
        "Use /plans to view subscription plans."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📜 *Available Plans:*\n\n"
    for key, plan in PLANS.items():
        text += f"{plan['name']} — ${plan['price']} USD\n"
    text += "\nUse /subscribe <plan> to start your subscription."
    await update.message.reply_text(text, parse_mode="Markdown")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("❌ Usage: /subscribe <plan>\nExample: /subscribe premium")
        return

    plan_key = context.args[0].lower()
    if plan_key not in PLANS:
        await update.message.reply_text("❌ Invalid plan. Use /plans to see available plans.")
        return

    expires = datetime.utcnow() + timedelta(days=30)

    async with async_session() as session:
        sub = await session.get(Subscription, user_id)
        if sub:
            sub.plan = plan_key
            sub.expires = expires
        else:
            sub = Subscription(user_id=user_id, plan=plan_key, expires=expires)
            session.add(sub)
        await session.commit()

    msg = (
        f"💳 Please pay the subscription amount to activate:\n\n"
        f"ETH Wallet: `{ETH_WALLET}`\n"
        f"SOL Wallet: `{SOL_WALLET}`\n"
        f"BTC Wallet: `{BTC_WALLET}`\n\n"
        f"Your plan: *{PLANS[plan_key]['name']}*\n"
        f"Amount: ${PLANS[plan_key]['price']} USD\n\n"
        "The bot will automatically verify your payment and activate the subscription."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    async with async_session() as session:
        sub = await session.get(Subscription, user_id)
        if sub:
            await update.message.reply_text(
                f"📄 You are subscribed to *{PLANS[sub.plan]['name']}* until {sub.expires}.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ No active subscription. Use /plans to subscribe.")

# -------------------------------
# Telegram Bot Setup
# -------------------------------
bot_app = Application.builder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("plans", plans))
bot_app.add_handler(CommandHandler("subscribe", subscribe))
bot_app.add_handler(CommandHandler("status", status))

# -------------------------------
# Blockchain Verification
# -------------------------------
w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
sol_client = AsyncClient(SOLANA_RPC_URL)

# --- ETH ---
async def check_eth_payments():
    async with async_session() as session:
        while True:
            subs = (await session.execute(
                Subscription.__table__.select()
            )).scalars().all()
            for sub in subs:
                if sub.tx_hash or sub.currency == "ETH":
                    continue
                # Scan last 10 blocks
                latest_block = w3.eth.block_number
                for i in range(latest_block-10, latest_block+1):
                    block = w3.eth.get_block(i, full_transactions=True)
                    for tx in block.transactions:
                        if tx.to and tx.to.lower() == ETH_WALLET.lower():
                            value_eth = w3.fromWei(tx.value, 'ether')
                            if value_eth >= PLANS[sub.plan]['price']/2000:  # rough USD->ETH
                                sub.tx_hash = tx.hash.hex()
                                sub.currency = "ETH"
                                sub.expires = datetime.utcnow() + timedelta(days=30)
                                await session.commit()
                                await bot_app.bot.send_message(
                                    chat_id=int(sub.user_id),
                                    text=f"✅ ETH payment received. Your *{PLANS[sub.plan]['name']}* subscription is now active!",
                                    parse_mode="Markdown"
                                )
                                await bot_app.bot.send_message(
                                    chat_id=ADMIN_CHAT_ID,
                                    text=f"💰 {sub.user_id} paid ETH {value_eth} for {sub.plan}."
                                )
            await asyncio.sleep(15)

# --- SOL ---
async def check_sol_payments():
    async with async_session() as session:
        wallet_pubkey = PublicKey(SOL_WALLET)
        while True:
            subs = (await session.execute(
                Subscription.__table__.select()
            )).scalars().all()
            for sub in subs:
                if sub.tx_hash or sub.currency == "SOL":
                    continue
                resp = await sol_client.get_signatures_for_address(wallet_pubkey, limit=10)
                for sig_info in resp.value:
                    if not sig_info.confirmations or sig_info.err:
                        continue
                    # For demo, assume SOL amount is enough
                    sub.tx_hash = sig_info.signature
                    sub.currency = "SOL"
                    sub.expires = datetime.utcnow() + timedelta(days=30)
                    await session.commit()
                    await bot_app.bot.send_message(
                        chat_id=int(sub.user_id),
                        text=f"✅ SOL payment received. Your *{PLANS[sub.plan]['name']}* subscription is now active!",
                        parse_mode="Markdown"
                    )
                    await bot_app.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f"💰 {sub.user_id} paid SOL for {sub.plan}."
                    )
            await asyncio.sleep(15)

# --- BTC ---
async def check_btc_payments():
    # Example using Bitcoin RPC, configure your BTC node credentials in ENV
    rpc_user = os.getenv("BTC_RPC_USER")
    rpc_pass = os.getenv("BTC_RPC_PASS")
    rpc_host = os.getenv("BTC_RPC_HOST", "127.0.0.1")
    rpc_port = os.getenv("BTC_RPC_PORT", "8332")
    rpc = AuthServiceProxy(f"http://{rpc_user}:{rpc_pass}@{rpc_host}:{rpc_port}")

    async with async_session() as session:
        while True:
            subs = (await session.execute(
                Subscription.__table__.select()
            )).scalars().all()
            for sub in subs:
                if sub.tx_hash or sub.currency == "BTC":
                    continue
                # List last 10 transactions
                txs = rpc.listtransactions("*", 10)
                for tx in txs:
                    if tx["address"] == BTC_WALLET and tx["category"] == "receive":
                        sub.tx_hash = tx["txid"]
                        sub.currency = "BTC"
                        sub.expires = datetime.utcnow() + timedelta(days=30)
                        await session.commit()
                        await bot_app.bot.send_message(
                            chat_id=int(sub.user_id),
                            text=f"✅ BTC payment received. Your *{PLANS[sub.plan]['name']}* subscription is now active!",
                            parse_mode="Markdown"
                        )
                        await bot_app.bot.send
