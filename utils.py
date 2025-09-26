# utils.py
import logging
import traceback
import asyncio
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# If you want logs to file (optional), uncomment:
# fh = logging.FileHandler('bot_errors.log')
# fh.setLevel(logging.ERROR)
# logger.addHandler(fh)

async def safe_run_async(func, *args, bot=None, owner_id=None, **kwargs):
    """
    Call an async function safely. Logs exception stack trace and optionally
    sends a Telegram alert to owner_id using provided bot object.
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"⚠️ Async error in {getattr(func, '__name__', str(func))}: {e}\n{traceback.format_exc()}")
        # send Telegram alert if bot and owner_id provided
        try:
            if bot and owner_id:
                text = f"⚠️ Error in `{getattr(func, '__name__', str(func))}`:\n{str(e)}"
                # don't await sending alert here if event loop might be blocked; schedule it
                await bot.send_message(chat_id=int(owner_id), text=text, parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to send error alert to owner")
        return None

def safe_run(func, *args, **kwargs):
    """
    Call a sync function safely. Logs exception and returns None on error.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"⚠️ Error in {getattr(func, '__name__', str(func))}: {e}\n{traceback.format_exc()}")
        return None
