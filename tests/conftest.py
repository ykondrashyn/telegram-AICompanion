import os
import sys
import pytest
from telegram.ext import ApplicationBuilder
from telegram import (Bot, User, Chat, Message, PhotoSize, Audio, Document,
                      Video, Voice, Sticker, Dice, Contact, Location, Poll,
                      PollOption)
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

def create_chat(chat_id=-100, title="Test Group", chat_type="group"):
    if chat_type == "private":
        return Chat(chat_id, "private", first_name=title)
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
                   chat_type="group", reply_to_bot=False, reply_to_msg=None,
                   caption=None, photo=False, command=False,
                   audio=False, document=False, video=False, voice=False,
                   sticker=False, dice=False, contact=False, location=False,
                   poll=False, forward_from_chat=None, forward_from_user=None, automatic=False):
    data = {
        "message_id": message_id,
        "date": int(datetime.now().timestamp()),
        "chat": create_chat(chat_id, chat_type=chat_type).to_dict(),
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
    if audio:
        a = Audio(file_id="a", file_unique_id="a", duration=1)
        data["audio"] = a.to_dict()
    if document:
        d = Document(file_id="d", file_unique_id="d")
        data["document"] = d.to_dict()
    if video:
        v = Video(file_id="v", file_unique_id="v", width=1, height=1, duration=1)
        data["video"] = v.to_dict()
    if voice:
        v = Voice(file_id="v", file_unique_id="v", duration=1)
        data["voice"] = v.to_dict()
    if sticker:
        s = Sticker(file_id="s", file_unique_id="s", width=1, height=1,
                     is_animated=False, is_video=False, type="regular")
        data["sticker"] = s.to_dict()
    if dice:
        d = Dice(1, "🎲")
        data["dice"] = d.to_dict()
    if contact:
        c = Contact("123", "User")
        data["contact"] = c.to_dict()
    if location:
        l = Location(1.0, 1.0)
        data["location"] = l.to_dict()
    if poll:
        p1 = PollOption("a", 0)
        poll_obj = Poll("id", "q", [p1], 0, False, True, "regular", False)
        data["poll"] = poll_obj.to_dict()
    if forward_from_chat is not None:
        data["forward_origin"] = {
            "type": "chat",
            "date": int(datetime.now().timestamp()),
            "sender_chat": forward_from_chat.to_dict(),
        }
    if forward_from_user is not None:
        data["forward_origin"] = {
            "type": "user",
            "date": int(datetime.now().timestamp()),
            "sender_user": forward_from_user.to_dict(),
        }
    if automatic:
        data["is_automatic_forward"] = True
    if reply_to_msg is not None:
        data["reply_to_message"] = reply_to_msg.to_dict()
    elif reply_to_bot:
        data["reply_to_message"] = create_bot_message(bot).to_dict()
    return Message.de_json(data, bot)

def create_join_message(bot, members, *, message_id=1, chat_id=-100, user_id=321, chat_type="group"):
    data = {
        "message_id": message_id,
        "date": int(datetime.now().timestamp()),
        "chat": create_chat(chat_id, chat_type=chat_type).to_dict(),
        "from": create_user(user_id).to_dict(),
        "new_chat_members": [m.to_dict() for m in members],
    }
    return Message.de_json(data, bot)
