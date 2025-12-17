import os
import sys
import asyncio
from dotenv import load_dotenv

# Try to import telegram libraries
try:
    from telegram import Bot
    from telegram.error import InvalidToken, TelegramError
    HAS_PTB = True
except ImportError:
    HAS_PTB = False
    print("⚠️  python-telegram-bot not installed → skipping live token test")

load_dotenv()

print("🔍 ICE GODS ICE DEVILS Bot Pre-Deploy Check\n")

errors = 0

# 1. Check .env exists
if not os.path.exists(".env"):
    print("❌ ERROR: .env file not found!")
    errors += 1
else:
    print("✅ .env file found")

# 2. Load and validate variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
WALLET = os.getenv("PAYMENT_WALLET", "").strip().lower()
ETHERSCAN = os.getenv("ETHERSCAN_KEY", "").strip()
CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID", "").strip()

if not TOKEN or len(TOKEN) < 40 or ":" not in TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing, empty, or invalid format")
    print("   → It should look like: 8018403994:AAFeLXCNybSuh1abjt7pdyjLpsyroKYP79Q")
    errors += 1
else:
    print("✅ TELEGRAM_BOT_TOKEN format looks good")

if not WALLET or not WALLET.startswith("0x") or len(WALLET) != 42:
    print("❌ ERROR: PAYMENT_WALLET invalid or missing")
    errors += 1
else:
    print("✅ PAYMENT_WALLET valid")

if not ETHERSCAN or len(ETHERSCAN) < 10:
    print("❌ ERROR: ETHERSCAN_KEY missing or too short")
    errors += 1
else:
    print("✅ ETHERSCAN_KEY present")

if not CHANNEL_ID or not CHANNEL_ID.startswith("-100"):
    print("⚠️  WARNING: PREMIUM_CHANNEL_ID invalid or missing")
else:
    print("✅ PREMIUM_CHANNEL_ID valid")

# 3. Live token test
if HAS_PTB and TOKEN and len(TOKEN) >= 40:
    print("\n🔄 Testing connection to Telegram with your bot token...")
    async def test_token():
        try:
            bot = Bot(token=TOKEN)
            me = await bot.get_me()
            print(f"✅ SUCCESS! Bot is @{me.username} ({me.first_name}) - Token is 100% VALID 🔥")
            return 0
        except InvalidToken:
            print("❌ ERROR: Invalid bot token - Telegram rejected it")
            print("   → Get a new one from @BotFather")
            return 1
        except TelegramError as e:
            print(f"⚠️  Telegram error: {e.message}")
            return 0  # Not critical
        except Exception as e:
            print(f"❌ Unexpected error during test: {e}")
            return 1

    errors += asyncio.run(test_token())
else:
    print("\n⚠️  Skipping live token test (token not loaded properly)")

# 4. Check required files
required_files = ["main.py", "requirements.txt", "Procfile", ".gitignore"]
missing = [f for f in required_files if not os.path.exists(f)]
if missing:
    print(f"❌ Missing files: {', '.join(missing)}")
    errors += len(missing)
else:
    print("✅ All required files present")

# Final result
print("\n" + "="*50)
if errors == 0:
    print("🎉 ALL CHECKS PASSED! BOT IS READY 🔥")
    print("   • Run: python main.py")
    print("   • Push to GitHub")
    print("   • Deploy to Render/Railway")
    print("\n   Your @ICEGODSICEDEVILS premium empire awaits 👑")
else:
    print(f"❌ {errors} issue(s) found - Fix before launch!")
    sys.exit(1)
