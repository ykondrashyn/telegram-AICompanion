import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update, Bot
from telegram.ext import CallbackContext
from ai_companion import handlers
from conftest import create_message, create_join_message, create_user, create_bot_message

# Dummy database stub
class DummyDB:
    def __init__(self):
        self.register_chat_called = False
        self.register_user_called = False
        self.register_message_called = False
        self.checked_user = False
        self.history = []

    async def add_history(self, uid, role, content, important=False):
        self.history.append((uid, role, content, important))

    async def get_history(self, uid, limit=10):
        return []

    async def register_chat(self, message):
        self.register_chat_called = True

    async def register_user(self, user):
        self.register_user_called = True

    async def register_message(self, message, message_sent):
        self.register_message_called = True

    async def check_user(self, message):
        self.checked_user = True
        return False

db_stub = DummyDB()

@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    db_stub.__init__()
    monkeypatch.setattr(handlers, "DB", db_stub)
    monkeypatch.setattr(handlers.messages, "DB", db_stub)
    monkeypatch.setattr(handlers.media, "DB", db_stub)
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
    monkeypatch.setattr(handlers.commands, "get_user_ai_mode", lambda uid: "grok")
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
    monkeypatch.setattr(handlers.commands, "set_user_ai_mode", AsyncMock(return_value=True))
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
    monkeypatch.setattr(handlers.commands, "set_user_prompt", AsyncMock(return_value=False))
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.prompt_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "Invalid" in send_mock.call_args.kwargs["text"]

@pytest.mark.asyncio
async def test_bot_reply_new_user(application, bot, monkeypatch):
    message = create_message(bot, "Hello", reply_to_bot=True)
    update = Update(update_id=4, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.messages, "generic_chat", lambda *a, **k: "DAN:hi")
    with patch("telegram.Message.reply_text", new=AsyncMock()) as reply_mock:
        await handlers.bot_reply_handler(update, context)
        assert reply_mock.await_count == 2

@pytest.mark.asyncio
async def test_offtopic_handler(application, bot, monkeypatch):
    message = create_message(bot, "/offtopic blah", command=True)
    update = Update(update_id=5, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.commands, "generic_chat", lambda *a, **k: "DAN:off")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.offtopic_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "off" in send_mock.call_args.kwargs["text"].lower()

@pytest.mark.asyncio
async def test_url_handler_generic(application, bot, monkeypatch):
    text = "@ai_bot Check https://example.com"
    message = create_message(bot, text)
    update = Update(update_id=6, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.media, "generic_chat", lambda *a, **k: "DAN:url")
    monkeypatch.setattr(handlers.media, "generate_link_preview", lambda url: {"title": "t", "description": "d", "thumbnail": "x"})
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.url_msg_handler(update, context)
        send_mock.assert_awaited_once()
        assert "url" in send_mock.call_args.kwargs["text"].lower()

@pytest.mark.asyncio
async def test_photo_handler(application, bot, monkeypatch):
    message = create_message(bot, caption="@ai_bot hi", photo=True)
    update = Update(update_id=7, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.media, "download_and_encode_image", AsyncMock(return_value=b"x"))
    monkeypatch.setattr(handlers.media, "generic_chat", lambda *a, **k: "DAN:pic")
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
    monkeypatch.setattr(handlers.messages, "generic_chat", lambda *a, **k: "DAN:rep")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.bot_reply_handler(update, context)
        send_mock.assert_not_called()
        assert not db_stub.checked_user

@pytest.mark.asyncio
async def test_bot_reply_existing_user(application, bot, monkeypatch):
    message = create_message(bot, "hello", reply_to_bot=True)
    update = Update(update_id=11, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(db_stub, "check_user", AsyncMock(return_value=True))
    monkeypatch.setattr(handlers.messages, "generic_chat", lambda *a, **k: "DAN:hi")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.bot_reply_handler(update, context)
        send_mock.assert_awaited_once()

@pytest.mark.asyncio
async def test_mode_set_invalid(application, bot, monkeypatch):
    message = create_message(bot, "/mode invalid", command=True)
    update = Update(update_id=12, message=message)
    context = await create_context(update, application)
    context.args = ["invalid"]
    monkeypatch.setattr(handlers.commands, "set_user_ai_mode", AsyncMock(return_value=False))
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.mode_command_handler(update, context)
        send_mock.assert_awaited_once()
        assert "Invalid" in send_mock.call_args.kwargs["text"]

@pytest.mark.asyncio
async def test_prompt_show_current(application, bot, monkeypatch):
    message = create_message(bot, "/prompt", command=True)
    update = Update(update_id=13, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.commands, "get_user_prompt", lambda uid: "dan")
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
    text = "@ai_bot Check https://youtu.be/abcdefghijk"
    message = create_message(bot, text)
    update = Update(update_id=16, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.media, "extract_video_id", lambda url: "abcdefghijk", raising=False)
    monkeypatch.setattr(handlers.media, "get_video_info_api", lambda vid: {"title": "t", "description": "d", "thumbnail": "th", "channelname": "c"})
    monkeypatch.setattr(handlers.media, "get_highest_rated_comments", lambda vid: ["c1"])
    monkeypatch.setattr(handlers.media, "helpers", type("H", (), {"escape_markdown": lambda t: t}), raising=False)
    monkeypatch.setattr(handlers.media, "generic_chat", lambda *a, **k: "DAN:yt")
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.url_msg_handler(update, context)
        assert send_mock.await_count == 2

@pytest.mark.asyncio
async def test_photo_handler_caption_url(application, bot, monkeypatch):
    message = create_message(bot, caption="@ai_bot Check https://example.com", photo=True)
    update = Update(update_id=17, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.media, "download_and_encode_image", AsyncMock(return_value=b"x"))
    monkeypatch.setattr(handlers.media, "generic_chat", lambda *a, **k: "DAN:pic")
    file_mock = AsyncMock(); file_mock.file_path = "https://x.com/p.jpg"
    monkeypatch.setattr(Bot, "getFile", AsyncMock(return_value=file_mock))
    from telegram.ext import ExtBot
    monkeypatch.setattr(ExtBot, "getFile", AsyncMock(return_value=file_mock))
    monkeypatch.setattr(handlers.media, "generate_link_preview", lambda url: {"title": "t", "description": "d", "thumbnail": "x"})
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.photo_msg_handler(update, context)
        send_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_reply_fork_new_user(application, bot, monkeypatch):
    replied = create_bot_message(bot, message_id=60)
    message = create_message(bot, "fork", reply_to_msg=replied, message_id=61, user_id=55)
    update = Update(update_id=18, message=message)
    context = await create_context(update, application)
    monkeypatch.setattr(handlers.messages, "generic_chat", lambda *a, **k: "DAN:fork")
    with patch("telegram.Message.reply_text", new=AsyncMock()) as reply_mock:
        await handlers.bot_reply_handler(update, context)
        assert reply_mock.await_count == 2
    assert (55, "assistant", "Bot message", True) in db_stub.history


@pytest.mark.asyncio
async def test_clear_history_command(application, bot):
    message = create_message(bot, "/clearhistory", command=True)
    update = Update(update_id=19, message=message)
    context = await create_context(update, application)
    with patch("telegram.Bot.send_message", new=AsyncMock()) as send_mock:
        await handlers.clear_history_command_handler(update, context)
        send_mock.assert_awaited_once()
