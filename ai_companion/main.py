import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from .config import TELEGRAM_BOT_TOKEN
from .handlers import (
    joined,
    offtopic_command_handler,
    mode_command_handler,
    prompt_command_handler,
    photo_msg_handler,
    bot_reply_handler,
    url_msg_handler,
    ignore_private
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def run():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("offtopic", offtopic_command_handler))
    application.add_handler(CommandHandler("mode", mode_command_handler))
    application.add_handler(CommandHandler("prompt", prompt_command_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_msg_handler))
    application.add_handler(MessageHandler(filters.REPLY, bot_reply_handler))
    application.add_handler(MessageHandler(filters.Entity("url"), url_msg_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, joined))
    application.add_handler(MessageHandler(filters.UpdateType.MESSAGE & (~filters.ALL), ignore_private))
    application.run_polling()

if __name__ == "__main__":
    run()
