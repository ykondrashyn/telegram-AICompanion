import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update
from telegram.ext import CallbackContext
from ai_companion import handlers
from conftest import create_message

# Dummy database stub
class DummyDB:
    def __init__(self):
        self.register_user_called = False
        self.register_message_called = False
        self.checked_user = False

    def register_chat(self, message):
        self.register_chat_called = True

    def register_user(self, user):
        self.register_user_called = True

    def register_message(self, message, message_sent):
        self.register_message_called = True

    def check_user(self, message):
        self.checked_user = True
        return False

db_stub = DummyDB()

@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    monkeypatch.setattr(handlers, "db", db_stub)
    yield
    handlers.global_prompt.reset()
    handlers.service_prompt.reset()

async def create_context(update, application):
    ctx = CallbackContext.from_update(update, application)
    ctx.args = []
    return ctx

@pytest.mark.asyncio
async def test_mode_show_current(application, bot, monkeypatch):
    message = create_message(bot, "/mode", command=True)
    update = Update(update_id=1, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "get_user_ai_mode", lambda uid: "grok")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.mode_command_handler(update, context)
        send_mock.assert_awaited_once()
        args, kwargs = send_mock.call_args
        assert "Current AI Mode" in kwargs["text"]

@pytest.mark.asyncio
async def test_mode_set_valid(application, bot, monkeypatch):
    message = create_message(bot, "/mode gpt", command=True)
    update = Update(update_id=2, message=message)
    context = await create_context(update, application)
    context.args = ["gpt"]
    monkeypatch.setattr(handlers, "set_user_ai_mode", lambda uid, mode: True)
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.mode_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "switched" in send_mock.call_args.kwargs["text"]

@pytest.mark.asyncio
async def test_prompt_invalid(application, bot, monkeypatch):
    message = create_message(bot, "/prompt unknown", command=True)
    update = Update(update_id=3, message=message)
    context = await create_context(update, application)
    context.args = ["unknown"]
    monkeypatch.setattr(handlers, "set_user_prompt", lambda uid, name: False)
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.prompt_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "Invalid" in send_mock.call_args.kwargs["text"]

@pytest.mark.asyncio
async def test_bot_reply_new_user(application, bot, monkeypatch):
    message = create_message(bot, "Hello", reply_to_bot=True)
    update = Update(update_id=4, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:hi")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.bot_reply_handler(update, context)
        # two replies: greeting and answer
        assert send_mock.await_count == 2

@pytest.mark.asyncio
async def test_offtopic_handler(application, bot, monkeypatch):
    message = create_message(bot, "/offtopic blah", command=True)
    update = Update(update_id=5, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:off")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.offtopic_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "off" in send_mock.call_args.kwargs["text"].lower()

@pytest.mark.asyncio
async def test_url_handler_generic(application, bot, monkeypatch):
    text = "Check https://example.com"
    message = create_message(bot, text)
    update = Update(update_id=6, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:url")
    monkeypatch.setattr(handlers, "generate_link_preview", lambda url: {"title": "t", "description": "d", "thumbnail": "x"})
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.url_msg_handler(update, context)
        send_mock.assert_awaited_once()
        assert "url" in send_mock.call_args.kwargs["text"].lower()
