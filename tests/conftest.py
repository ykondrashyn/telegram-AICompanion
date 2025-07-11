import os
import sys
import pytest
from telegram.ext import ApplicationBuilder
from telegram import Bot, User, Chat, Message, PhotoSize
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture()
def application():
    app = ApplicationBuilder().token("TEST_TOKEN").build()
    app.bot._bot_user = User(99999, "Bot", True, username="ai_bot")
    return app

@pytest.fixture()
def bot(application):
    return application.bot

def create_user(user_id=123, is_bot=False, first_name="User", username="user"):
    return User(user_id, first_name, is_bot, username=username)

def create_chat(chat_id=-100, title="Test Group"):
    return Chat(chat_id, "group", title=title)

def create_bot_message(bot, message_id=999, chat_id=-100):
    bot_user = User(99999, "Bot", True, username="ai_bot")
    data = {
        "message_id": message_id,
        "date": int(datetime.now().timestamp()),
        "chat": create_chat(chat_id).to_dict(),
        "from": bot_user.to_dict(),
        "text": "Bot message",
    }
    return Message.de_json(data, bot)

def create_message(bot, text=None, *, message_id=1, user_id=123, chat_id=-100,
                   reply_to_bot=False, caption=None, photo=False, command=False):
    data = {
        "message_id": message_id,
        "date": int(datetime.now().timestamp()),
        "chat": create_chat(chat_id).to_dict(),
        "from": create_user(user_id).to_dict(),
    }
    if text is not None:
        data["text"] = text
        if command:
            data["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text)}]
    if caption is not None:
        data["caption"] = caption
    if photo:
        p = PhotoSize(file_id="1", file_unique_id="1", width=10, height=10)
        data["photo"] = [p.to_dict()]
    if reply_to_bot:
        data["reply_to_message"] = create_bot_message(bot).to_dict()
    return Message.de_json(data, bot)
