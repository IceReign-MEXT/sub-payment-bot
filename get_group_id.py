import asyncio
from telegram import Bot

BOT_TOKEN = "8018403994:AAF1mAi9_DNOEOLYvxAFWzy4fJZAc2L4aZA"
bot = Bot(token=BOT_TOKEN)

async def main():
    print("➡️ Send a message in your premium group now.")
    input("Press Enter after sending...")

    # Replace with the ID of the channel or any known chat for testing
    # If unknown, you can test by sending a message from the bot
    chat = await bot.get_chat(-1002384609234)  # your channel ID
    print("✅ Chat info:", chat)

asyncio.run(main())
