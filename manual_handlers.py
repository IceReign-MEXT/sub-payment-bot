import functools
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("ManualHandler")

def manual_safe_run(func):
    """
    Decorator to run critical functions safely.
    If an exception occurs, it logs a warning without crashing the bot.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"[ManualHandler] Issue detected in {func.__name__}: {e}")
            # Optionally: you can add more actions here, like sending a notification
            return None
    return wrapper
