import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update, Bot
from telegram.ext import CallbackContext
from ai_companion import handlers
from conftest import create_message, create_join_message, create_user

# Dummy database stub
class DummyDB:
    def __init__(self):
        self.register_chat_called = False
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
    db_stub.__init__()
    monkeypatch.setattr(handlers, "db", db_stub)
    yield
    handlers.global_prompt.reset()
    handlers.service_prompt.reset()
    db_stub.__init__()

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

@pytest.mark.asyncio
async def test_photo_handler(application, bot, monkeypatch):
    message = create_message(bot, caption="hi", photo=True)
    update = Update(update_id=7, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "download_and_encode_image", AsyncMock(return_value=b"x"))
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:pic")
    file_mock = AsyncMock(); file_mock.file_path = "https://x.com/p.jpg"
    monkeypatch.setattr(Bot, "getFile", AsyncMock(return_value=file_mock))
    from telegram.ext import ExtBot
    monkeypatch.setattr(ExtBot, "getFile", AsyncMock(return_value=file_mock))
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.photo_msg_handler(update, context)
        send_mock.assert_awaited_once()

@pytest.mark.asyncio
async def test_joined_bot_added(application, bot, monkeypatch):
    join_msg = create_join_message(bot, [bot._bot_user])
    update = Update(update_id=8, message=join_msg)
    context = await create_context(update, application)
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.joined(update, context)
        send_mock.assert_awaited_once()
        assert db_stub.register_chat_called

@pytest.mark.asyncio
async def test_joined_regular_user(application, bot, monkeypatch):
    join_msg = create_join_message(bot, [create_user(55)])
    update = Update(update_id=9, message=join_msg)
    context = await create_context(update, application)
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.joined(update, context)
        send_mock.assert_not_called()
        assert db_stub.register_chat_called is False

@pytest.mark.asyncio
async def test_reply_not_to_bot(application, bot, monkeypatch):
    other = create_message(bot, "hi", user_id=55, message_id=50)
    message = create_message(bot, "reply", reply_to_msg=other, message_id=51)
    update = Update(update_id=10, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:rep")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.bot_reply_handler(update, context)
        send_mock.assert_awaited_once()
        assert not db_stub.checked_user

@pytest.mark.asyncio
async def test_bot_reply_existing_user(application, bot, monkeypatch):
    message = create_message(bot, "hello", reply_to_bot=True)
    update = Update(update_id=11, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(db_stub, "check_user", lambda m: True)
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:hi")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.bot_reply_handler(update, context)
        send_mock.assert_awaited_once()

@pytest.mark.asyncio
async def test_mode_set_invalid(application, bot, monkeypatch):
    message = create_message(bot, "/mode invalid", command=True)
    update = Update(update_id=12, message=message)
    context = await create_context(update, application)
    context.args = ["invalid"]
    monkeypatch.setattr(handlers, "set_user_ai_mode", lambda uid, mode: False)
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.mode_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "Invalid" in send_mock.call_args.kwargs["text"]

@pytest.mark.asyncio
async def test_prompt_show_current(application, bot, monkeypatch):
    message = create_message(bot, "/prompt", command=True)
    update = Update(update_id=13, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "get_user_prompt", lambda uid: "dan")
    monkeypatch.setattr(handlers.prompt_loader, "list_prompts", lambda: ["dan", "friendly"])
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.prompt_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "Current Prompt" in send_mock.call_args.kwargs["text"]

@pytest.mark.asyncio
async def test_prompt_reload(application, bot, monkeypatch):
    message = create_message(bot, "/prompt reload", command=True)
    update = Update(update_id=14, message=message)
    context = await create_context(update, application)
    context.args = ["reload"]
    monkeypatch.setattr(handlers.prompt_loader, "reload_prompts", lambda: None)
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.prompt_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "reloaded" in send_mock.call_args.kwargs["text"].lower()

@pytest.mark.asyncio
async def test_ignore_private(application, bot):
    message = create_message(bot, "hi", chat_id=100, chat_type="private")
    update = Update(update_id=15, message=message)
    context = await create_context(update, application)
    with patch("telegram.Message.reply_text", new=AsyncMock()) as send_mock:
        await handlers.ignore_private(update, context)
        send_mock.assert_awaited_once_with('I only respond in group chats!')

@pytest.mark.asyncio
async def test_url_handler_youtube(application, bot, monkeypatch):
    text = "Check https://youtu.be/abcdefghijk"
    message = create_message(bot, text)
    update = Update(update_id=16, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "extract_video_id", lambda url: "abcdefghijk", raising=False)
    monkeypatch.setattr(handlers, "get_video_info_api", lambda vid: {"title": "t", "description": "d", "thumbnail": "th", "channelname": "c"})
    monkeypatch.setattr(handlers, "get_highest_rated_comments", lambda vid: ["c1"])
    monkeypatch.setattr(handlers, "helpers", type("H", (), {"escape_markdown": lambda t: t}), raising=False)
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:yt")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.url_msg_handler(update, context)
        assert send_mock.await_count == 2

@pytest.mark.asyncio
async def test_photo_handler_caption_url(application, bot, monkeypatch):
    message = create_message(bot, caption="Check https://example.com", photo=True)
    update = Update(update_id=17, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers, "download_and_encode_image", AsyncMock(return_value=b"x"))
    monkeypatch.setattr(handlers, "generic_chat", lambda *a, **k: "DAN:pic")
    file_mock = AsyncMock(); file_mock.file_path = "https://x.com/p.jpg"
    monkeypatch.setattr(Bot, "getFile", AsyncMock(return_value=file_mock))
    from telegram.ext import ExtBot
    monkeypatch.setattr(ExtBot, "getFile", AsyncMock(return_value=file_mock))
    monkeypatch.setattr(handlers, "generate_link_preview", lambda url: {"title": "t", "description": "d", "thumbnail": "x"})
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.photo_msg_handler(update, context)
        send_mock.assert_awaited_once()
