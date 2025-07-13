import logging
import time
import socket
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.error import NetworkError, TimedOut
from .config import TELEGRAM_BOT_TOKEN
from .handlers import (
    joined,
    offtopic_command_handler,
    mode_command_handler,
    prompt_command_handler,
    clear_history_command_handler,
    photo_msg_handler,
    bot_reply_handler,
    url_msg_handler,
    ignore_private,
    mention_handler
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def check_internet_connection():
    """Check if we have internet connectivity."""
    try:
        # Try to connect to Google's DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

async def error_handler(update, context):
    """Log errors caused by Updates."""
    logger.error(f'Update {update} caused error {context.error}')

    # Try to send a user-friendly message if possible
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Sorry, something went wrong. Please try again later."
            )
        except Exception:
            pass  # If we can't send a message, just log the error

def run():
    max_retries = 5
    retry_delay = 10  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"Starting Telegram bot (attempt {attempt + 1}/{max_retries})")
            application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

            # Add error handler
            application.add_error_handler(error_handler)

            # Add message handlers
            application.add_handler(CommandHandler("offtopic", offtopic_command_handler))
            application.add_handler(CommandHandler("mode", mode_command_handler))
            application.add_handler(CommandHandler("prompt", prompt_command_handler))
            application.add_handler(CommandHandler("clearhistory", clear_history_command_handler))
            # Only handle messages from actual users (not forwarded from channels)
            application.add_handler(MessageHandler(filters.PHOTO & filters.User(), photo_msg_handler))
            application.add_handler(MessageHandler(filters.REPLY & filters.User(), bot_reply_handler))
            application.add_handler(MessageHandler(filters.Entity("url") & filters.User(), url_msg_handler))
            application.add_handler(MessageHandler(filters.Entity("mention") & filters.User(), mention_handler))
            application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, joined))
            application.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, ignore_private))

            # Run with network error handling
            application.run_polling(
                allowed_updates=None,
                drop_pending_updates=True
            )
            break  # If we get here, the bot ran successfully

        except NetworkError as e:
            logger.error(f"Network error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                # Check internet connectivity before retrying
                if not check_internet_connection():
                    logger.warning("No internet connection detected. Waiting for connectivity...")
                    while not check_internet_connection():
                        time.sleep(5)
                    logger.info("Internet connection restored.")

                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Max retries reached. Bot failed to start.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise

if __name__ == "__main__":
    run()
